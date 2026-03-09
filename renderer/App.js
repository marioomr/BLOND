const { createApp } = Vue

// ── Waveform canvas — waveform + sección coloreada + timestamps ───────────────
const WaveformCanvas = {
  props: {
    waveform:    { type: Array,  default: () => [] },
    energyCurve: { type: Array,  default: () => [] },
    sections:    { type: Array,  default: () => [] },
    duration:    { type: Number, default: 0 },
    height:      { type: Number, default: 80 }
  },
  template: `
    <div style="width:100%;">
      <canvas ref="canvas" :height="height"
        style="width:100%;display:block;border-radius:8px 8px 0 0;"></canvas>
      <div style="position:relative;height:22px;">
        <canvas ref="ruler_canvas" height="22"
          style="width:100%;display:block;border-radius:0 0 8px 8px;"></canvas>
      </div>
    </div>
  `,
  mounted()  { this.$nextTick(() => this.draw()) },
  updated()  { this.$nextTick(() => this.draw()) },
  watch: {
    waveform() { this.$nextTick(() => this.draw()) },
    sections() { this.$nextTick(() => this.draw()) },
    duration() { this.$nextTick(() => this.draw()) },
  },
  methods: {
    draw() { this.drawWaveform(); this.drawRuler() },
    drawWaveform() {
      const canvas = this.$refs.canvas
      if (!canvas) return
      const W = canvas.offsetWidth || 500
      canvas.width = W
      const H = this.height
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#1e293b'
      ctx.fillRect(0, 0, W, H)

      if (!this.waveform.length) {
        ctx.fillStyle = 'rgba(100,116,139,0.4)'
        ctx.fillRect(0, H / 2 - 1, W, 2)
        return
      }

      const mid = H / 2
      const data = this.waveform
      const barW = W / data.length

      // Section color bands
      if (this.sections.length && this.duration > 0) {
        this.sections.forEach(sec => {
          const x1 = (sec.start / this.duration) * W
          const x2 = (sec.end   / this.duration) * W
          ctx.fillStyle = sec.color + '22'
          ctx.fillRect(x1, 0, x2 - x1, H)
          ctx.fillStyle = sec.color + '88'
          ctx.fillRect(x1, 0, 1.5, H)
        })
      }

      // Waveform bars
      data.forEach((v, i) => {
        const x = i * barW
        const barH = Math.max(1, v * mid * 0.92)
        const r = Math.round(56  + v * 199)
        const g = Math.round(189 - v * 80)
        const b = Math.round(248 - v * 120)
        ctx.fillStyle = `rgba(${r},${g},${b},0.9)`
        ctx.fillRect(x, mid - barH, Math.max(1, barW - 0.5), barH * 2)
      })

      // Energy curve overlay
      if (this.energyCurve.length > 1) {
        ctx.beginPath()
        ctx.strokeStyle = 'rgba(234,179,8,0.5)'
        ctx.lineWidth = 1.5
        this.energyCurve.forEach((v, i) => {
          const x = (i / (this.energyCurve.length - 1)) * W
          const y = H - v * H * 0.88 - 2
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        })
        ctx.stroke()
      }

      // Section type labels on waveform
      if (this.sections.length && this.duration > 0) {
        ctx.font = '9px system-ui, sans-serif'
        ctx.textBaseline = 'top'
        this.sections.forEach(sec => {
          const x    = (sec.start / this.duration) * W + 3
          const secW = ((sec.end - sec.start) / this.duration) * W
          if (secW < 20) return
          ctx.fillStyle = sec.color + 'cc'
          ctx.fillText(sec.type, x, 3)
        })
      }
    },
    drawRuler() {
      const canvas = this.$refs.ruler_canvas
      if (!canvas || !this.duration) return
      const W = canvas.offsetWidth || 500
      canvas.width = W
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#0f172a'
      ctx.fillRect(0, 0, W, 22)

      if (!this.sections.length) return

      ctx.font = '9px system-ui, sans-serif'
      ctx.textBaseline = 'middle'

      this.sections.forEach(sec => {
        const x = (sec.start / this.duration) * W
        const m = Math.floor(sec.start / 60)
        const s = Math.floor(sec.start % 60)
        const label = `${m}:${String(s).padStart(2, '0')}`
        // Tick
        ctx.fillStyle = sec.color + 'aa'
        ctx.fillRect(x, 0, 1.5, 8)
        // Time label — clamp so it doesn't overflow right edge
        const textX = Math.min(x + 2, W - 26)
        ctx.fillStyle = sec.color
        ctx.fillText(label, textX, 15)
      })

      // End time (right-aligned)
      const em = Math.floor(this.duration / 60)
      const es = Math.floor(this.duration % 60)
      ctx.fillStyle = '#475569'
      ctx.textAlign = 'right'
      ctx.fillText(`${em}:${String(es).padStart(2,'0')}`, W - 2, 15)
      ctx.textAlign = 'left'
    }
  }
}

// ── Bar meter ─────────────────────────────────────────────────────────────────
const BarMeter = {
  props: {
    label: String,
    value: { type: Number, default: 0 },
    color: { type: String,   default: '#38bdf8' },
    fmt:   { type: Function, default: v => Math.round(v * 100) + '%' }
  },
  template: `
    <div class="flex items-center gap-2 w-full">
      <span class="text-slate-400 text-xs w-20 shrink-0 text-right">{{ label }}</span>
      <div class="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div class="h-full rounded-full transition-all duration-700"
             :style="{ width: (Math.min(value,1) * 100) + '%', background: color }"></div>
      </div>
      <span class="text-slate-300 text-xs w-8 shrink-0">{{ fmt(value) }}</span>
    </div>
  `
}

// ── Main app ──────────────────────────────────────────────────────────────────
createApp({
  components: { WaveformCanvas, BarMeter },

  template: `
  <div
    class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white flex flex-col"
    style="font-family:system-ui,sans-serif; -webkit-app-region:no-drag;"
    @dragover.prevent
    @drop.prevent="onFileDrop"
  >
    <!-- Title bar — only this strip drags the window -->
    <div class="h-8 shrink-0 flex items-center px-4"
         style="-webkit-app-region:drag; user-select:none;">
      <span class="text-slate-600 text-xs ml-20">BLOND</span>
    </div>

    <!-- Scrollable content -->
    <div class="flex-1 overflow-y-auto px-5 pb-6 space-y-4">

      <!-- Header row -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight leading-none">BLOND</h1>
          <p class="text-slate-400 text-xs mt-0.5">Track DNA · Stem Splitter</p>
        </div>
        <div v-if="songPath"
          class="flex items-center gap-2 bg-slate-700 rounded-lg px-3 py-1.5 max-w-xs min-w-0">
          <span class="text-cyan-400 text-xs flex-shrink-0">♪</span>
          <span class="text-slate-200 text-xs truncate">{{ songName }}</span>
        </div>
      </div>

      <!-- ── DNA RESULT ─────────────────────────────────────────────── -->
      <template v-if="dna">

        <!-- Waveform + ruler timestamps -->
        <div class="bg-slate-800 rounded-xl p-3 border border-slate-700">
          <WaveformCanvas
            :waveform="dna.waveform"
            :energyCurve="dna.energy_curve"
            :sections="dna.sections"
            :duration="dna.duration"
            :height="80"
          />
          <!-- Section legend pills -->
          <div v-if="dna.sections.length" class="flex flex-wrap gap-1.5 mt-2.5">
            <span v-for="sec in sectionLegend" :key="sec.type"
              class="text-xs px-2 py-0.5 rounded-full"
              :style="{
                background: sec.color + '28',
                color: sec.color,
                border: '1px solid ' + sec.color + '66'
              }">
              {{ sec.type }}
            </span>
          </div>
        </div>

        <!-- BPM · Camelot · Key -->
        <div class="grid grid-cols-4 gap-2">
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-cyan-400 text-xl font-bold leading-tight">{{ dna.bpm }}</span>
            <span class="text-slate-400 text-xs">BPM</span>
            <span class="text-slate-500 text-xs">±{{ Math.round((1 - dna.tempo_stability) * 100) }}%</span>
          </div>
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5">
            <span class="text-yellow-400 text-xl font-bold leading-tight">{{ dna.camelot }}</span>
            <span class="text-slate-400 text-xs">Camelot</span>
            <span class="text-slate-500 text-xs capitalize">{{ dna.mode }}</span>
          </div>
          <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 flex flex-col items-center gap-0.5 col-span-2">
            <span class="text-white text-sm font-semibold text-center leading-tight">{{ dna.key }}</span>
            <span class="text-slate-400 text-xs">Musical Key</span>
            <span class="text-slate-500 text-xs">{{ dna.loudness_db }} dB</span>
          </div>
        </div>

        <!-- Meter bars -->
        <div class="bg-slate-800 rounded-xl p-3 border border-slate-700 space-y-2.5">
          <BarMeter label="Energy"       :value="dna.energy / 100"  color="#38bdf8" :fmt="v => Math.round(v * 100)" />
          <BarMeter label="Danceability" :value="dna.danceability"  color="#a78bfa" :fmt="v => (v*100).toFixed(0)+'%'" />
          <BarMeter label="Brightness"   :value="dna.brightness"    color="#fbbf24" :fmt="v => (v*100).toFixed(0)+'%'" />
          <BarMeter label="Bass"         :value="dna.bass_strength" color="#f87171" :fmt="v => (v*100).toFixed(0)+'%'" />
          <BarMeter label="Compression"  :value="dna.compression"   color="#34d399" :fmt="v => (v*100).toFixed(0)+'%'" />
        </div>

        <!-- Stats row -->
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
            <span class="text-slate-500 text-xs">{{ dna.sections.length }} sections</span>
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

      </template>

      <!-- ── DNA PROGRESS ───────────────────────────────────────────────── -->
      <div v-else-if="isAnalyzing"
        class="bg-slate-800 rounded-xl p-5 border border-slate-700 space-y-3">
        <div class="flex items-center justify-between">
          <p class="text-slate-300 text-sm font-medium">Analyzing track DNA...</p>
          <span class="text-cyan-400 text-sm font-bold">{{ dnaProgress }}%</span>
        </div>
        <div class="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full transition-all duration-300"
               :style="{ width: dnaProgress + '%' }"></div>
        </div>
        <p class="text-slate-500 text-xs">{{ dnaStep }}</p>
      </div>

      <!-- ── EMPTY STATE ────────────────────────────────────────────────── -->
      <div v-else
        class="bg-slate-800 rounded-xl p-8 border border-dashed border-slate-600 flex flex-col items-center gap-2 text-center">
        <span class="text-4xl">🎧</span>
        <p class="text-slate-300 text-sm font-medium mt-1">Drop a track or click below</p>
        <p class="text-slate-500 text-xs">BPM · Key · Energy · Structure · Waveform</p>
      </div>

      <!-- ── STEM SPLITTER ──────────────────────────────────────────────── -->
      <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div class="px-4 py-2 border-b border-slate-700">
          <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">Stem Splitter</span>
        </div>

        <div v-if="isProcessing" class="p-4 space-y-3">
          <p class="text-slate-300 text-sm">Splitting stems...</p>
          <div class="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-300"
                 :style="{ width: splitProgress + '%' }"></div>
          </div>
          <p class="text-slate-500 text-xs">{{ splitProgress }}%</p>
        </div>

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

        <div v-else class="p-4 space-y-2">
          <div class="flex gap-2">
            <button @click="selectOutput"
              class="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm py-2 rounded-lg transition-colors">
              {{ outputPath ? '✓ Output set' : 'Set Output Folder' }}
            </button>
            <button @click="split" :disabled="!songPath || !outputPath"
              class="flex-1 bg-green-700 hover:bg-green-600 disabled:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium py-2 rounded-lg transition-colors">
              Split Stems
            </button>
          </div>
          <p v-if="splitError" class="text-red-400 text-xs">{{ splitError }}</p>
        </div>
      </div>

      <div v-if="dnaError"
        class="bg-red-500 bg-opacity-10 border border-red-500 text-red-300 text-xs p-3 rounded-lg">
        {{ dnaError }}
      </div>

    </div>

    <!-- ── BOTTOM ACTION BAR ──────────────────────────────────────────────── -->
    <div class="shrink-0 border-t border-slate-700 bg-slate-900 px-4 py-3 flex gap-2">
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
      songPath:      null,
      songName:      '',
      outputPath:    null,
      dna:           null,
      isAnalyzing:   false,
      dnaError:      null,
      dnaProgress:   0,
      dnaStep:       '',
      splitProgress: 0,
      isProcessing:  false,
      isDone:        false,
      splitError:    null,
    }
  },

  computed: {
    sectionLegend() {
      if (!this.dna?.sections) return []
      const seen = new Set()
      return this.dna.sections.filter(s => {
        if (seen.has(s.type)) return false
        seen.add(s.type)
        return true
      })
    }
  },

  mounted() {
    window.api.onDnaProgress(({ pct, step }) => {
      this.dnaProgress = pct
      if (step) this.dnaStep = step
    })
  },

  beforeUnmount() {
    window.api.offDnaProgress()
  },

  methods: {
    // Drag & drop
    onFileDrop(e) {
      const file = e.dataTransfer?.files?.[0]
      if (!file) return
      const ext = file.name.split('.').pop().toLowerCase()
      if (!['mp3', 'wav', 'flac', 'aiff', 'aif', 'm4a'].includes(ext)) return
      this.songPath  = file.path
      this.songName  = file.name.replace(/\.[^/.]+$/, '')
      this.dna       = null
      this.dnaError  = null
      this.splitError = null
      this.isDone    = false
    },

    async selectSong() {
      const p = await window.api.selectFile()
      if (!p) return
      this.songPath  = p
      this.songName  = p.split('/').pop().replace(/\.[^/.]+$/, '')
      this.dna       = null
      this.dnaError  = null
      this.splitError = null
      this.isDone    = false
    },

    async selectOutput() {
      this.outputPath = await window.api.selectOutput()
    },

    async analyzeTrack() {
      if (!this.songPath) return
      this.isAnalyzing = true
      this.dnaError    = null
      this.dna         = null
      this.dnaProgress = 0
      this.dnaStep     = 'Starting...'
      try {
        const result = await window.api.analyzeTrack(this.songPath)
        if (result.success) {
          this.dnaProgress = 100
          this.dna = result
        } else {
          this.dnaError = result.error || 'Analysis failed'
        }
      } catch (err) {
        this.dnaError = err.message || 'Track DNA analysis failed'
      } finally {
        this.isAnalyzing = false
      }
    },

    async split() {
      if (!this.songPath || !this.outputPath) return
      this.isProcessing  = true
      this.isDone        = false
      this.splitError    = null
      this.splitProgress = 0
      try {
        const demucsPromise = window.api.runDemucs(this.songPath, this.outputPath)
        await this.waitForSplitCompletion()
        await demucsPromise
        this.isDone = true
      } catch (err) {
        this.splitError = err.message || 'Processing failed'
        this.isProcessing = false
      }
    },

    async waitForSplitCompletion() {
      return new Promise((resolve, reject) => {
        const check = async (attempts = 0) => {
          if (attempts > 600) { this.isProcessing = false; reject(new Error('Timeout')); return }
          try {
            const logs = await window.api.readLogs()
            if (!logs.length) { setTimeout(() => check(attempts + 1), 500); return }
            const content = await window.api.readLogFile(logs[0])
            if (!content?.trim()) { setTimeout(() => check(attempts + 1), 500); return }
            if (content.includes('ERROR:')) {
              const line = content.split('\n').find(l => l.includes('ERROR:'))
              this.isProcessing = false
              reject(new Error(line?.split('ERROR:')[1]?.trim() || 'Failed'))
              return
            }
            if (content.includes('DONE')) {
              this.splitProgress = 100; this.isProcessing = false; resolve(); return
            }
            const lines = content.split('\n')
            for (let i = lines.length - 1; i >= 0; i--) {
              const m = lines[i].match(/(\d{1,3})%\|/)
              if (m) { this.splitProgress = parseInt(m[1]); break }
            }
          } catch {}
          setTimeout(() => check(attempts + 1), 500)
        }
        check()
      })
    },

    resetSplit() { this.isDone = false; this.splitProgress = 0; this.splitError = null },

    formatDuration(s) {
      const m = Math.floor(s / 60)
      return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}`
    }
  }
}).mount('#app')
