const { createApp } = Vue

createApp({
  template: `
    <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div class="w-full max-w-md">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-4xl font-bold text-white mb-2">BLOND</h1>
          <p class="text-slate-400 text-sm">Stem Splitter</p>
        </div>

        <!-- Card -->
        <div class="bg-slate-700 bg-opacity-50 backdrop-blur rounded-2xl shadow-2xl p-8 space-y-6 border border-slate-600">
          
          <!-- Processing State -->
          <div v-if="isProcessing" class="space-y-4">
            <p class="text-white text-sm font-medium truncate">{{ songName }}</p>
            <div class="w-full h-2 bg-slate-600 rounded-full overflow-hidden">
              <div 
                class="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                :style="{ width: progress + '%' }"
              ></div>
            </div>
            <p class="text-slate-400 text-xs">{{ progress }}%</p>
          </div>

          <!-- Done State -->
          <div v-else-if="isDone" class="text-center space-y-3 py-8">
            <div class="text-5xl">✓</div>
            <p class="text-white font-medium">Done!</p>
            <p class="text-slate-400 text-sm">Vocal and instrumental files saved</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="bg-red-500 bg-opacity-10 border border-red-500 text-red-300 text-sm p-3 rounded-lg">
            {{ error }}
          </div>

          <!-- Default State -->
          <div v-else class="text-center mb-4">
            <p class="text-slate-300 text-sm">Select an audio file to separate</p>
          </div>

          <!-- Buttons -->
          <div v-if="!isProcessing && !isDone" class="space-y-3">
            <button
              @click="selectSong"
              class="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-medium py-3 rounded-lg transition-colors duration-200 active:opacity-75"
            >
              {{ songPath ? '✓ Song' : 'Select Song' }}
            </button>

            <button
              @click="selectOutput"
              class="w-full bg-slate-600 hover:bg-slate-500 text-white font-medium py-3 rounded-lg transition-colors duration-200"
            >
              {{ outputPath ? '✓ Output' : 'Select Output' }}
            </button>

            <button
              @click="split"
              :disabled="!songPath || !outputPath"
              class="w-full bg-green-600 hover:bg-green-700 disabled:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-50 text-white font-medium py-3 rounded-lg transition-colors duration-200 active:opacity-75"
            >
              Split
            </button>
          </div>

          <!-- Reset Button -->
          <button
            v-if="isDone"
            @click="reset"
            class="w-full bg-slate-600 hover:bg-slate-500 text-white font-medium py-2 rounded-lg text-sm transition-colors"
          >
            Split Another
          </button>
        </div>
      </div>
    </div>
  `,
  data() {
    return {
      songPath: null,
      outputPath: null,
      progress: 0,
      isProcessing: false,
      isDone: false,
      error: null,
      songName: ''
    }
  },
  methods: {
    async selectSong() {
      this.songPath = await window.api.selectFile()
      if (this.songPath) {
        this.songName = this.songPath.split('/').pop().replace(/\.[^/.]+$/, '')
      }
    },
    async selectOutput() {
      this.outputPath = await window.api.selectOutput()
    },
    async split() {
      if (!this.songPath || !this.outputPath) return

      this.isProcessing = true
      this.isDone = false
      this.error = null
      this.progress = 0

      try {
        // Start the demucs process (it will run in background)
        const demucsPromise = window.api.runDemucs(this.songPath, this.outputPath)
        
        // Start monitoring progress while demucs runs
        await this.waitForCompletion()
        
        // Wait for the demucs process to actually finish
        await demucsPromise
        
        this.isDone = true
      } catch (err) {
        this.error = err.message || 'Processing failed'
        this.isProcessing = false
      }
    },
    async waitForCompletion() {
      return new Promise((resolve, reject) => {
        const checkProgress = async (attempts = 0) => {
          if (attempts > 600) { // 5 minutes timeout (checks every 500ms)
            this.isProcessing = false
            reject(new Error('Processing timeout (5 minutes)'))
            return
          }

          try {
            const logs = await window.api.readLogs()
            if (logs.length === 0) {
              // Log file doesn't exist yet, wait and retry
              setTimeout(() => checkProgress(attempts + 1), 500)
              return
            }

            const content = await window.api.readLogFile(logs[0])
            
            // If log is empty, wait a bit more
            if (!content || content.trim().length === 0) {
              setTimeout(() => checkProgress(attempts + 1), 500)
              return
            }
            
            // Check for ERROR first
            if (content.includes('ERROR:')) {
              const errorLine = content.split('\n').find(l => l.includes('ERROR:'))
              const error = errorLine ? errorLine.split('ERROR:')[1].trim() : 'Processing failed'
              this.isProcessing = false
              reject(new Error(error))
              return
            }

            // Check for DONE
            if (content.includes('DONE')) {
              this.progress = 100
              this.isProcessing = false
              console.log('[✓] Progress: 100% - DONE')
              resolve()
              return
            }

            // Parse progress percentage from lines like "  0%|" or " 10%|" or "100%|"
            const lines = content.split('\n')
            
            // Search backwards to find the most recent progress line
            for (let i = lines.length - 1; i >= 0; i--) {
              const line = lines[i]
              const match = line.match(/(\d{1,3})%\|/)
              if (match) {
                const newProgress = parseInt(match[1])
                this.progress = newProgress
                console.log(`[Progress] ${newProgress}%`)
                break
              }
            }

          } catch (err) {
            console.error('[Error reading logs]:', err)
          }

          // Keep checking every 500ms
          setTimeout(() => checkProgress(attempts + 1), 500)
        }

        checkProgress()
      })
    },
    reset() {
      this.songPath = null
      this.outputPath = null
      this.progress = 0
      this.isDone = false
      this.error = null
      this.songName = ''
    }
  }
}).mount('#app')

