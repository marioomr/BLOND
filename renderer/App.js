const { createApp } = Vue

// ── Waveform canvas component ─────────────────────────────────────────────────
const WaveformCanvas = {
  props: {
    waveform: { type: Array, default: () => [] },
    energyCurve: { type: Array, default: () => [] },
    sections: { type: Array, default: () => [] },
    duration: { type: Number, default: 0 },
    height: { type: Number, default: 72 }
  },
  template: `<canvas ref="canvas" :height="height" style="width:100%;display:block;border-radius:8px;"></canvas>`,
  mounted() { this.draw() },
  watch: {
    waveform() { this.draw() },
    sections() { this.draw() }
  },
  methods: {
    draw() {
      const canvas = this.$refs.canvas
      if (!canvas) return
      const W = canvas.offsetWidth || 500
      canvas.width = W
      const H = this.height
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, W, H)

      if (!this.waveform.length) {
        ctx.fillStyle = 'rgba(100,116,139,0.3)'
        ctx.fillRect(0, H / 2 - 1, W, 2)
        return
      }

      const mid = H / 2
      const data = this.waveform
      const barW = W / data.length

      // Section color bands (behind waveform)
      if (this.sections.length && this.duration > 0) {
        this.sections.forEach(sec => {
          const x1 = (sec.start / this.duration) * W
          const x2 = (sec.end / this.duration) * W
          ctx.fillStyle = sec.color + '28'
          ctx.fillRect(x1, 0, x2 - x1, H)
        })
      }

      // Waveform bars
      data.forEach((v, i) => {
        const x = i * barW
        const barH = Math.max(1, v * mid * 0.95)

        // Color by energy intensity
        const intensity = v
        const r = Math.round(56 + intensity * 199)
        const g = Math.round(189 - intensity * 80)
        const b = Math.round(248 - intensity * 120)
        ctx.fillStyle = `rgba(${r},${g},${b},0.85)`
        ctx.fillRect(x, mid - barH, Math.max(1, barW - 0.5), barH * 2)
      })

      // Energy curve overlay
      if (this.energyCurve.length > 1) {
        ctx.beginPath()
        ctx.strokeStyle = 'rgba(234,179,8,0.55)'
        ctx.lineWidth = 1.5
        this.energyCurve.forEach((v, i) => {
          const x = (i / (this.energyCurve.length - 1)) * W
          const y = H - v * H * 0.9 - 2
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        })
        ctx.stroke()
      }
    }
  }
}

// ── Circular stat badge ───────────────────────────────────────────────────────
const StatBadge = {
  props: {
    label: String,
    value: [String, Number],
    sub: { type: String, default: '' },
    color: { type: String, default: 'cyan' }
  },
  template: `
    <div class="flex flex-col items-center gap-1">
      <div :class="'text-' + color + '-400 text-lg font-bold leading-none'">{{ value }}</div>
      <div class="text-slate-400 text-xs leading-none">{{ label }}</div>
      <div v-if="sub" class="text-slate-500 text-xs leading-none">{{ sub }}</div>
    </div>
  `
}

// ── Bar meter component ───────────────────────────────────────────────────────
const BarMeter = {
  props: {
    label: String,
    value: { type: Number, default: 0 },    // 0-1
    color: { type: String, default: '#38bdf8' },
    fmt: { type: Function, default: (v) => Math.round(v * 100) + '%' }
  },
  template: `
    <div class="flex items-center gap-2 w-full">
      <span class="text-slate-400 text-xs w-20 shrink-0 text-right">{{ label }}</span>
      <div class="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div class="h-full rounded-full transition-all duration-700"
             :style="{ width: (value * 100) + '%', background: color }"></div>
      </div>
      <span class="text-slate-300 text-xs w-8 shrink-0">{{ fmt(value) }}</span>
    </div>
  `
}

// ── Main app ──────────────────────────────────────────────────────────────────
createApp({
  components: { WaveformCanvas, StatBadge, BarMeter },

  template: `
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white flex flex-col" style="font-family: system-ui, sans-serif;">

    <!-- Title bar drag region -->
    <div class="h-8 shrink-0" style="-webkit-app-region: drag;"></div>

    <!-- Main scroll area -->
    <div class="flex-1 overflow-y-auto px-5 pb-6 space-y-4" style="-webkit-app-region: no-drag;">

      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">BLOND</h1>
          <p class="text-slate-400 text-xs mt-0.5">Track DNA · Stem Splitter</p>
        </div>
        <!-- File chip -->
        <div v-if="songPath" class="flex items-center gap-2 bg-slate-700 rounded-lg px-3 py-1.5 max-w-xs">
          <span class="text-cyan-400 text-xs">♪</span>
          <span class="text-slate-200 text-xs truncate">{{ songName }}</span>
        </div>
      </div>

      <!-- ── TRACK DNA PANEL ─────────────────────────────────────────── -->
      <div v-if="dna" class="space-y-3">

        <!-- Waveform + sections -->
        <div class="bg-slate-800 rounded-xl p-3 border border-slate-700">
          <WaveformCanvas
            :waveform="dna.waveform"
            :energyCurve="dna.energy_curve"
            :sections="dna.sections"
            :duration="dna.duration"
            :height="72"
          />
          <!-- Section legend -->
          <div v-if="dna.sections.length" class="flex flex-wrap gap-1.5 mt-2">
            <span v-for="sec in sectionLegend" :key="sec.type"
              class="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
              :style="{ background: sec.color + '33', color: sec.color, borderColor: sec.color, border: '1px solid' + sec.color + '66' }">
              {{ sec.type }}
            </span>
          </div>
        </div>

        <!-- Key stats row: BPM · Key · Camelot · Energy -->
        <div class="grid grid-cols-4 gap-2">
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-cyan-400 text-xl font-bold">{{ dna.bpm }}</span>
            <span class="text-slate-400 text-xs">BPM</span>
            <span class="text-slate-500 text-xs">±{{ Math.round((1 - dna.tempo_stability) * 100) }}%</span>
          </div>
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-yellow-400 text-lg font-bold leading-tight">{{ dna.camelot }}</span>
            <span class="text-slate-400 text-xs">Camelot</span>
            <span class="text-slate-500 text-xs capitalize">{{ dna.mode }}</span>
          </div>
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5 col-span-2">
            <span class="text-white text-sm font-semibold">{{ dna.key }}</span>
            <span class="text-slate-400 text-xs">Musical Key</span>
            <span class="text-slate-500 text-xs">{{ dna.loudness_db }} dB</span>
          </div>
        </div>

        <!-- Meter bars: Energy · Dance · Brightness · Bass · Compression -->
        <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 space-y-2.5">
          <BarMeter label="Energy" :value="dna.energy / 100" color="#38bdf8" :fmt="v => Math.round(v * 100)" />
          <BarMeter label="Danceability" :value="dna.danceability" color="#a78bfa" :fmt="v => (v * 100).toFixed(0) + '%'" />
          <BarMeter label="Brightness" :value="dna.brightness" color="#fbbf24" :fmt="v => (v * 100).toFixed(0) + '%'" />
          <BarMeter label="Bass" :value="dna.bass_strength" color="#f87171" :fmt="v => (v * 100).toFixed(0) + '%'" />
          <BarMeter label="Compression" :value="dna.compression" color="#34d399" :fmt="v => (v * 100).toFixed(0) + '%'" />
        </div>

        <!-- Dynamics row -->
        <div class="grid grid-cols-3 gap-2">
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-emerald-400 text-lg font-bold">{{ dna.dynamic_range }}</span>
            <span class="text-slate-400 text-xs">Dyn Range</span>
            <span class="text-slate-500 text-xs">dB</span>
          </div>
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-purple-400 text-lg font-bold">{{ dna.mix_compatibility }}</span>
            <span class="text-slate-400 text-xs">Mix Score</span>
            <span class="text-slate-500 text-xs">/100</span>
          </div>
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-orange-400 text-lg font-bold">{{ formatDuration(dna.duration) }}</span>
            <span class="text-slate-400 text-xs">Duration</span>
            <span class="text-slate-500 text-xs">{{ dna.drops.length }} drops</span>
          </div>
        </div>

        <!-- Mood tags -->
        <div v-if="dna.mood && dna.mood.length" class="flex items-center gap-2 flex-wrap">
          <span class="text-slate-400 text-xs">Mood</span>
          <span v-for="tag in dna.mood" :key="tag"
            class="bg-violet-600 bg-opacity-30 border border-violet-500 text-violet-300 px-2.5 py-0.5 rounded-full text-xs capitalize">
            {{ tag }}
          </span>
        </div>

        <!-- Drops & Breakdowns timeline -->
        <div v-if="dna.drops.length || dna.breakdowns.length" class="bg-slate-800 rounded-xl p-3 border border-slate-700">
          <p class="text-slate-400 text-xs mb-2">Structure Markers</p>
          <div class="flex flex-wrap gap-2">
            <span v-for="t in dna.drops" :key="'drop-'+t"
              class="flex items-center gap-1 text-xs bg-red-500 bg-opacity-20 border border-red-500 text-red-400 px-2 py-0.5 rounded">
              ▼ {{ formatDuration(t) }}
            </span>
            <span v-for="t in dna.breakdowns" :key="'bd-'+t"
              class="flex items-center gap-1 text-xs bg-emerald-500 bg-opacity-20 border border-emerald-500 text-emerald-400 px-2 py-0.5 rounded">
              ◆ {{ formatDuration(t) }}
            </span>
          </div>
        </div>

      </div>

      <!-- ── ANALYZING STATE ──────────────────────────────────────────── -->
      <div v-else-if="isAnalyzing" class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col items-center gap-3">
        <div class="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-cyan-500 to-violet-500 animate-pulse rounded-full" style="width: 100%"></div>
        </div>
        <p class="text-slate-400 text-sm">Scanning track DNA...</p>
      </div>

      <!-- ── EMPTY STATE ─────────────────────────────────────────────── -->
      <div v-else class="bg-slate-800 rounded-xl p-6 border border-dashed border-slate-600 flex flex-col items-center gap-2 text-center">
        <span class="text-3xl">🎧</span>
        <p class="text-slate-300 text-sm font-medium">Drop a track to analyze</p>
        <p class="text-slate-500 text-xs">BPM · Key · Energy · Sections · Waveform</p>
      </div>

      <!-- ── SPLIT SECTION ───────────────────────────────────────────── -->
      <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div class="px-4 py-2 border-b border-slate-700 flex items-center gap-2">
          <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">Stem Splitter</span>
        </div>

        <!-- Processing -->
        <div v-if="isProcessing" class="p-4 space-y-3">
          <p class="text-slate-300 text-sm">Splitting stems...</p>
          <div class="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300 rounded-full"
                 :style="{ width: progress + '%' }"></div>
          </div>
          <p class="text-slate-500 text-xs">{{ progress }}%</p>
        </div>

        <!-- Done -->
        <div v-else-if="isDone" class="p-4 flex items-center gap-3">
          <span class="text-2xl">✓</span>
          <div>
            <p class="text-white text-sm font-medium">Stems saved!</p>
            <p class="text-slate-400 text-xs">Vocals + instrumental ready</p>
          </div>
          <button @click="resetSplit"
            class="ml-auto text-xs text-slate-400 hover:text-white border border-slate-600 hover:border-slate-400 px-3 py-1 rounded-lg transition-colors">
            Reset
          </button>
        </div>

        <!-- Controls -->
        <div v-else class="p-4 space-y-2">
          <div class="flex gap-2">
            <button @click="selectOutput"
              class="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm py-2 rounded-lg transition-colors">
              {{ outputPath ? '✓ Output set' : 'Set Output Folder' }}
            </button>
            <button @click="split"
              :disabled="!songPath || !outputPath"
              class="flex-1 bg-green-700 hover:bg-green-600 disabled:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40 text-white text-sm font-medium py-2 rounded-lg transition-colors">
              Split Stems
            </button>
          </div>
          <div v-if="splitError" class="text-red-400 text-xs">{{ splitError }}</div>
        </div>
      </div>

      <!-- ── ERROR ──────────────────────────────────────────────────── -->
      <div v-if="dnaError" class="bg-red-500 bg-opacity-10 border border-red-500 text-red-300 text-xs p-3 rounded-lg">
        {{ dnaError }}
      </div>

    </div>

    <!-- ── BOTTOM ACTION BAR ──────────────────────────────────────────── -->
    <div class="shrink-0 border-t border-slate-700 bg-slate-900 px-4 py-3 flex gap-2" style="-webkit-app-region: no-drag;">
      <button @click="selectSong"
        class="flex-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium text-sm py-2.5 rounded-lg transition-all active:opacity-80">
        {{ songPath ? '♫ Change Track' : '＋ Select Track' }}
      </button>
      <button v-if="songPath && !isAnalyzing" @click="analyzeTrack"
        class="flex-1 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white font-medium text-sm py-2.5 rounded-lg transition-all active:opacity-80">
        🧬 Analyze DNA
      </button>
    </div>

  </div>
  `,

  data() {
    return {
      // File state
      songPath: null,
      songName: '',
      outputPath: null,

      // Track DNA
      dna: null,
      isAnalyzing: false,
      dnaError: null,

      // Splitter
      progress: 0,
      isProcessing: false,
      isDone: false,
      splitError: null,
    }
  },

  computed: {
    sectionLegend() {
      if (!this.dna || !this.dna.sections) return []
      const seen = new Set()
      return this.dna.sections.filter(s => {
        if (seen.has(s.type)) return false
        seen.add(s.type)
        return true
      })
    }
  },

  methods: {
    // ── File selection ──────────────────────────────────────────────────
    async selectSong() {
      const path = await window.api.selectFile()
      if (!path) return
      this.songPath = path
      this.songName = path.split('/').pop().replace(/\.[^/.]+$/, '')
      this.dna = null
      this.dnaError = null
      this.splitError = null
      this.isDone = false
    },

    async selectOutput() {
      this.outputPath = await window.api.selectOutput()
    },

    // ── Track DNA ───────────────────────────────────────────────────────
    async analyzeTrack() {
      if (!this.songPath) return
      this.isAnalyzing = true
      this.dnaError = null
      this.dna = null

      try {
        const result = await window.api.analyzeTrack(this.songPath)
        if (result.success) {
          this.dna = result
          console.log('[DNA] BPM:', result.bpm, '| Key:', result.key, '| Energy:', result.energy)
        } else {
          this.dnaError = result.error || 'Analysis failed'
        }
      } catch (err) {
        this.dnaError = err.message || 'Track DNA analysis failed'
        console.error('[DNA Error]:', err)
      } finally {
        this.isAnalyzing = false
      }
    },

    // ── Stem splitter ───────────────────────────────────────────────────
    async split() {
      if (!this.songPath || !this.outputPath) return
      this.isProcessing = true
      this.isDone = false
      this.splitError = null
      this.progress = 0

      try {
        const demucsPromise = window.api.runDemucs(this.songPath, this.outputPath)
        await this.waitForCompletion()
        await demucsPromise
        this.isDone = true
      } catch (err) {
        this.splitError = err.message || 'Processing failed'
        this.isProcessing = false
      }
    },

    async waitForCompletion() {
      return new Promise((resolve, reject) => {
        const checkProgress = async (attempts = 0) => {
          if (attempts > 600) {
            this.isProcessing = false
            reject(new Error('Processing timeout (5 minutes)'))
            return
          }

          try {
            const logs = await window.api.readLogs()
            if (!logs.length) {
              setTimeout(() => checkProgress(attempts + 1), 500)
              return
            }

            const content = await window.api.readLogFile(logs[0])
            if (!content || !content.trim()) {
              setTimeout(() => checkProgress(attempts + 1), 500)
              return
            }

            if (content.includes('ERROR:')) {
              const errorLine = content.split('\n').find(l => l.includes('ERROR:'))
              const msg = errorLine ? errorLine.split('ERROR:')[1].trim() : 'Processing failed'
              this.isProcessing = false
              reject(new Error(msg))
              return
            }

            if (content.includes('DONE')) {
              this.progress = 100
              this.isProcessing = false
              resolve()
              return
            }

            const lines = content.split('\n')
            for (let i = lines.length - 1; i >= 0; i--) {
              const match = lines[i].match(/(\d{1,3})%\|/)
              if (match) {
                this.progress = parseInt(match[1])
                break
              }
            }
          } catch (e) {
            console.error('[Splitter progress error]:', e)
          }

          setTimeout(() => checkProgress(attempts + 1), 500)
        }

        checkProgress()
      })
    },

    resetSplit() {
      this.isDone = false
      this.progress = 0
      this.splitError = null
    },

    // ── Helpers ──────────────────────────────────────────────────────────
    formatDuration(seconds) {
      const m = Math.floor(seconds / 60)
      const s = Math.floor(seconds % 60)
      return `${m}:${String(s).padStart(2, '0')}`
    }
  }
}).mount('#app')
