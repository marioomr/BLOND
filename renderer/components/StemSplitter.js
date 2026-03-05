export default {
  name: 'StemSplitter',
  data() {
    return {
      song: null,
      output: null,
      status: '',
      isProcessing: false,
      progress: 0,
      errorMessage: ''
    }
  },
  methods: {
    async selectSong() {
      try {
        const file = await window.api.selectFile()
        if (file) {
          this.song = file
          this.errorMessage = ''
        }
      } catch (error) {
        this.errorMessage = 'Error selecting song: ' + error.message
      }
    },

    async selectOutput() {
      try {
        const folder = await window.api.selectOutput()
        if (folder) {
          this.output = folder
          this.errorMessage = ''
        }
      } catch (error) {
        this.errorMessage = 'Error selecting output folder: ' + error.message
      }
    },

    async split() {
      if (!this.song || !this.output) {
        this.errorMessage = 'Please select both song and output folder'
        return
      }

      this.isProcessing = true
      this.status = 'Separating...'
      this.progress = 0
      this.errorMessage = ''

      try {
        await window.api.runDemucs(this.song, this.output)
        this.status = '✅ Done!'
        this.progress = 100
        
        // Reset after 3 seconds
        setTimeout(() => {
          this.song = null
          this.output = null
          this.status = ''
          this.progress = 0
        }, 3000)
      } catch (error) {
        this.errorMessage = error.message
        this.status = '❌ Error'
        console.error(error)
      } finally {
        this.isProcessing = false
      }
    }
  },
  template: `
    <div class="container">
      <div class="card">
        <div class="header">
          <h1>🎵 BLOND Stem Splitter</h1>
          <p class="subtitle">Separate vocals and instrumentals from your music</p>
        </div>

        <div class="form-section">
          <!-- Song Selection -->
          <div class="form-group">
            <label class="label">Select Song</label>
            <button 
              @click="selectSong"
              :disabled="isProcessing"
              class="btn btn-primary"
            >
              📁 Choose Audio File
            </button>
            <p v-if="song" class="file-path">{{ song }}</p>
          </div>

          <!-- Output Selection -->
          <div class="form-group">
            <label class="label">Output Folder</label>
            <button 
              @click="selectOutput"
              :disabled="isProcessing"
              class="btn btn-primary"
            >
              📁 Choose Output Folder
            </button>
            <p v-if="output" class="file-path">{{ output }}</p>
          </div>

          <!-- Split Button -->
          <div class="form-group">
            <button 
              @click="split"
              :disabled="!song || !output || isProcessing"
              class="btn btn-success btn-lg"
            >
              <span v-if="!isProcessing">🎬 Split Audio</span>
              <span v-else>⏳ Processing...</span>
            </button>
          </div>

          <!-- Progress Bar -->
          <div v-if="isProcessing" class="progress-bar">
            <div class="progress-fill" :style="{ width: progress + '%' }"></div>
          </div>

          <!-- Status Messages -->
          <div v-if="status" :class="['status-message', status.includes('Done') ? 'success' : 'error']">
            {{ status }}
          </div>

          <div v-if="errorMessage" class="error-message">
            ⚠️ {{ errorMessage }}
          </div>
        </div>
      </div>
    </div>
  `
}
