const { createApp } = Vue

// ── Waveform canvas ───────────────────────────────────────────────────────────
const WaveformCanvas = {
  props: {
    waveform:    { type: Array,  default: () => [] },
    energyCurve: { type: Array,  default: () => [] },
    duration:    { type: Number, default: 0 },
    height:      { type: Number, default: 56 }
  },
  template: `<canvas ref="canvas" :height="height"
    style="width:100%;display:block;"></canvas>`,
  mounted()  { this.$nextTick(() => this.draw()) },
  updated()  { this.$nextTick(() => this.draw()) },
  watch: {
    waveform()    { this.$nextTick(() => this.draw()) },
    energyCurve() { this.$nextTick(() => this.draw()) },
  },
  methods: {
    draw() {
      const canvas = this.$refs.canvas
      if (!canvas) return
      const dpr = window.devicePixelRatio || 1
      const W   = canvas.offsetWidth  || 400
      const H   = this.height
      canvas.width  = W * dpr
      canvas.height = H * dpr
      const ctx = canvas.getContext('2d')
      ctx.scale(dpr, dpr)

      // ── background ─────────────────────────────────────────────────────────
      ctx.fillStyle = '#0d1117'
      ctx.fillRect(0, 0, W, H)

      const mid = H / 2

      // ── flat centre line (empty state) ─────────────────────────────────────
      if (!this.waveform.length) {
        ctx.strokeStyle = 'rgba(148,163,184,0.12)'
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(W, mid); ctx.stroke()
        return
      }

      // ── downsample to a bar count that looks clean at this width ───────────
      const BAR_COUNT = Math.min(this.waveform.length, Math.floor(W / 3))
      const step      = this.waveform.length / BAR_COUNT
      const bars      = []
      for (let i = 0; i < BAR_COUNT; i++) {
        const lo  = Math.floor(i * step)
        const hi  = Math.min(Math.floor((i + 1) * step), this.waveform.length)
        let   max = 0
        for (let j = lo; j < hi; j++) max = Math.max(max, this.waveform[j])
        bars.push(max)
      }

      // Normalise so the loudest bar = 1
      const peak = Math.max(...bars, 0.001)
      const norm = bars.map(v => v / peak)

      // ── bar geometry ───────────────────────────────────────────────────────
      const totalGap = BAR_COUNT * 1           // 1px gap between each bar
      const barW     = (W - totalGap) / BAR_COUNT
      const slot     = barW + 1

      // Reserve bottom 12px for timestamps → waveform uses top (H-12)px
      const waveH   = H - 12
      const waveMid = waveH / 2

      // ── draw bars (mirrored, symmetrical) ──────────────────────────────────
      // 1st pass — filled bars
      norm.forEach((n, i) => {
        const x    = i * slot
        const half = Math.max(1, n * waveMid * 0.88)

        // Gradient: brighter in the middle, fades toward top/bottom
        const grad = ctx.createLinearGradient(0, waveMid - half, 0, waveMid + half)
        // Intensity-based colour: quiet=dim indigo, loud=bright cyan→white
        const lightness = 0.25 + n * 0.75
        const r = Math.round(34  + n * 152)   // 34→186
        const g = Math.round(130 + n * 95)    // 130→225
        const b = Math.round(246 + n * 9)     // 246→255
        const aTop = (lightness * 0.55).toFixed(2)
        const aMid = (lightness * 0.95).toFixed(2)
        grad.addColorStop(0,   `rgba(${r},${g},${b},${aTop})`)
        grad.addColorStop(0.45,`rgba(${r},${g},${b},${aMid})`)
        grad.addColorStop(0.5, `rgba(220,240,255,${(lightness * 0.9).toFixed(2)})`)
        grad.addColorStop(0.55,`rgba(${r},${g},${b},${aMid})`)
        grad.addColorStop(1,   `rgba(${r},${g},${b},${aTop})`)

        ctx.fillStyle = grad
        ctx.beginPath()
        ctx.roundRect(x, waveMid - half, Math.max(1, barW), half * 2, 1)
        ctx.fill()
      })

      // 2nd pass — thin bright spine down the centre of each loud bar
      ctx.globalCompositeOperation = 'screen'
      norm.forEach((n, i) => {
        if (n < 0.45) return
        const x    = i * slot + barW * 0.5 - 0.5
        const half = n * waveMid * 0.88
        const a    = (n * 0.35).toFixed(3)
        const spine = ctx.createLinearGradient(0, waveMid - half, 0, waveMid + half)
        spine.addColorStop(0,   `rgba(186,230,253,0)`)
        spine.addColorStop(0.5, `rgba(224,242,254,${a})`)
        spine.addColorStop(1,   `rgba(186,230,253,0)`)
        ctx.fillStyle = spine
        ctx.fillRect(x, waveMid - half, 1, half * 2)
      })
      ctx.globalCompositeOperation = 'source-over'

      // ── energy curve — subtle amber ribbon along the bottom of the waveform ─
      if (this.energyCurve.length > 1) {
        const ec = this.energyCurve
        ctx.save()
        ctx.beginPath()
        ec.forEach((val, i) => {
          const x = (i / (ec.length - 1)) * W
          const y = waveH - val * waveMid * 0.72 - 2
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        })
        ctx.strokeStyle = 'rgba(251,191,36,0.55)'
        ctx.lineWidth   = 1
        ctx.lineJoin    = 'round'
        ctx.shadowColor = 'rgba(251,191,36,0.4)'
        ctx.shadowBlur  = 4
        ctx.stroke()
        ctx.restore()
      }

      // ── timestamp row (bottom 12px) ────────────────────────────────────────
      if (this.duration > 0) {
        const rowY = waveH + 2
        ctx.font         = '9px system-ui,sans-serif'
        ctx.textBaseline = 'top'
        ctx.fillStyle    = 'rgba(100,116,139,0.7)'

        // Separator line
        ctx.fillRect(0, waveH, W, 1)

        // Interval: every 30s or 60s depending on length
        const interval = this.duration <= 120 ? 30 : this.duration <= 300 ? 60 : 120
        for (let t = interval; t < this.duration - 8; t += interval) {
          const x = (t / this.duration) * W
          ctx.fillRect(x, waveH, 1, 3)
          ctx.fillText(this._fmt(t), x + 2, rowY)
        }
        // Start
        ctx.textAlign = 'left'
        ctx.fillText('0:00', 3, rowY)
        // End
        ctx.textAlign = 'right'
        ctx.fillText(this._fmt(this.duration), W - 3, rowY)
        ctx.textAlign = 'left'
      }
    },

    _fmt(s) {
      return `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`
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
    class="min-h-screen text-white flex flex-col"
    style="font-family:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;
           background:#0a0e17; -webkit-app-region:no-drag;"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onFileDrop"
  >
    <!-- ── Titlebar drag strip ─────────────────────────────────────────────── -->
    <div class="h-9 shrink-0" style="-webkit-app-region:drag;"></div>

    <!-- ── Track header ───────────────────────────────────────────────────── -->
    <!-- Drop overlay — flashes green when a valid file is dragged over -->
    <div v-if="isDragging"
         class="absolute inset-0 z-50 flex flex-col items-center justify-center rounded-xl pointer-events-none"
         style="background:rgba(34,197,94,0.13); border:2px dashed rgba(34,197,94,0.7); margin:8px;">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 mb-2" style="color:#22c55e;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm12-3c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zM9 10l12-3"/>
      </svg>
      <p class="text-base font-semibold" style="color:#22c55e;">Drop to load track</p>
    </div>

    <!-- Cover art + title + artist block -->
    <div class="px-4 pb-4 flex flex-col items-center gap-3 text-center">
      <!-- Cover art — bigger, prominent -->
      <div class="w-24 h-24 rounded-2xl overflow-hidden flex items-center justify-center shrink-0"
           style="background:#131d2e; box-shadow:0 0 0 1px rgba(255,255,255,0.07), 0 8px 32px rgba(0,0,0,0.5);">
        <img v-if="dna && dna.cover" :src="dna.cover" class="w-full h-full object-cover" />
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-10 h-10" style="color:#1e3a5f;" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z"/>
        </svg>
      </div>
      <!-- Title -->
      <div class="w-full">
        <p class="text-base font-bold leading-tight truncate text-white px-2"
           style="letter-spacing:-0.01em;">
          {{ dna ? (dna.title || songName) : (songName || 'BLOND') }}
        </p>
        <p class="text-sm leading-tight truncate mt-1 font-medium"
           style="color:#64748b;">
          {{ dna && dna.artist ? dna.artist : 'Track DNA · Stem Splitter' }}
        </p>
      </div>
    </div>

    <!-- ── Scrollable body ────────────────────────────────────────────────── -->
    <div class="flex-1 overflow-y-auto px-4 pb-5 space-y-3">

      <!-- ════ DNA RESULT ════════════════════════════════════════════════════ -->
      <template v-if="dna">

        <!-- Waveform -->
        <div class="rounded-xl overflow-hidden" style="box-shadow:0 0 0 1px rgba(255,255,255,0.05);">
          <WaveformCanvas
            :waveform="dna.waveform"
            :energyCurve="dna.energy_curve"
            :duration="dna.duration"
            :height="56"
          />
        </div>

        <!-- ── Primary stats row: BPM · Key · Camelot · Length ────────────── -->
        <div class="grid grid-cols-4 gap-2">
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-xl font-bold leading-none" style="color:#38bdf8;">{{ dna.bpm }}</span>
            <span class="text-xs" style="color:#475569;">BPM</span>
          </div>
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-base font-bold leading-none text-white">{{ dna.key.split(' ')[0] }}</span>
            <span class="text-xs capitalize" style="color:#475569;">{{ dna.mode }}</span>
          </div>
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-xl font-bold leading-none" style="color:#eab308;">{{ dna.camelot }}</span>
            <span class="text-xs" style="color:#475569;">Camelot</span>
          </div>
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-base font-bold leading-none text-white">{{ formatDuration(dna.duration) }}</span>
            <span class="text-xs" style="color:#475569;">Length</span>
          </div>
        </div>

        <!-- ── Secondary stats row: Loudness · Dyn Range · Mix Score ─────── -->
        <div class="grid grid-cols-3 gap-2">
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-lg font-bold leading-none" style="color:#34d399;">{{ dna.loudness_db }}</span>
            <span class="text-xs" style="color:#475569;">Loudness dB</span>
          </div>
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-lg font-bold leading-none" style="color:#a78bfa;">{{ dna.dynamic_range }}</span>
            <span class="text-xs" style="color:#475569;">Dyn Range dB</span>
          </div>
          <div class="rounded-xl flex flex-col items-center justify-center gap-1 py-3"
               style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
            <span class="text-lg font-bold leading-none" style="color:#fb923c;">{{ dna.mix_compatibility }}<span class="text-xs font-normal" style="color:#475569;">/100</span></span>
            <span class="text-xs" style="color:#475569;">Mix Score</span>
          </div>
        </div>

        <!-- ── Audio Profile ──────────────────────────────────────────────── -->
        <div class="rounded-xl px-3 pt-2.5 pb-3 space-y-2"
             style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
          <p class="text-xs font-medium uppercase tracking-widest mb-1" style="color:#334155;">Audio Profile</p>
          <BarMeter label="Energy"       :value="dna.energy / 100"  color="#38bdf8" :fmt="v => Math.round(v*100)+'%'" />
          <BarMeter label="Danceability" :value="dna.danceability"  color="#a78bfa" :fmt="v => Math.round(v*100)+'%'" />
          <BarMeter label="Brightness"   :value="dna.brightness"    color="#fbbf24" :fmt="v => Math.round(v*100)+'%'" />
          <BarMeter label="Bass"         :value="dna.bass_strength" color="#f87171" :fmt="v => Math.round(v*100)+'%'" />
          <BarMeter label="Compression"  :value="dna.compression"   color="#34d399" :fmt="v => Math.round(v*100)+'%'" />
        </div>

        <!-- ── Mood ───────────────────────────────────────────────────────── -->
        <div v-if="dna.mood && dna.mood.length" class="flex items-center gap-2 flex-wrap px-0.5">
          <span class="text-xs uppercase tracking-widest" style="color:#334155;">Mood</span>
          <span v-for="tag in dna.mood" :key="tag"
            class="text-xs px-2.5 py-0.5 rounded-full capitalize font-medium"
            style="background:rgba(139,92,246,0.15); color:#a78bfa; border:1px solid rgba(139,92,246,0.25);">
            {{ tag }}
          </span>
        </div>

      </template>

      <!-- ════ ANALYZING ═════════════════════════════════════════════════════ -->
      <div v-else-if="isAnalyzing"
           class="rounded-xl p-5 space-y-3"
           style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium text-white">Analyzing...</p>
          <span class="text-sm font-bold tabular-nums" style="color:#38bdf8;">{{ dnaProgress }}%</span>
        </div>
        <div class="w-full h-1 rounded-full overflow-hidden" style="background:#1e293b;">
          <div class="h-full rounded-full transition-all duration-200"
               style="background:linear-gradient(90deg,#06b6d4,#8b5cf6);"
               :style="{ width: dnaProgress + '%' }"></div>
        </div>
        <p class="text-xs" style="color:#475569;">{{ dnaStep }}</p>
      </div>

      <!-- ════ EMPTY STATE ═══════════════════════════════════════════════════ -->
      <div v-else
           class="rounded-xl p-8 flex flex-col items-center gap-2 text-center"
           style="background:#111827; border:1px dashed rgba(255,255,255,0.08);">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 mb-1" style="color:#1e3a5f;" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z"/>
        </svg>
        <p class="text-sm font-medium text-white">Drop a track to start</p>
        <p class="text-xs" style="color:#334155;">BPM · Key · Camelot · Energy · Waveform</p>
      </div>

      <!-- ════ STEM SPLITTER ═════════════════════════════════════════════════ -->
      <div class="rounded-xl overflow-hidden"
           style="background:#111827; border:1px solid rgba(255,255,255,0.05);">
        <div class="px-3 py-2 flex items-center gap-2"
             style="border-bottom:1px solid rgba(255,255,255,0.05);">
          <span class="w-1.5 h-1.5 rounded-full" style="background:#22c55e;"></span>
          <span class="text-xs font-medium uppercase tracking-widest" style="color:#475569;">Stem Splitter</span>
        </div>

        <!-- Processing -->
        <div v-if="isProcessing" class="p-4 space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-sm text-white">Splitting stems...</p>
            <span class="text-sm font-bold tabular-nums" style="color:#22c55e;">{{ splitProgress }}%</span>
          </div>
          <div class="w-full h-1 rounded-full overflow-hidden" style="background:#1e293b;">
            <div class="h-full rounded-full transition-all duration-300"
                 style="background:linear-gradient(90deg,#06b6d4,#22c55e);"
                 :style="{ width: splitProgress + '%' }"></div>
          </div>
        </div>

        <!-- Done -->
        <div v-else-if="isDone" class="p-4 flex items-center gap-3">
          <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
               style="background:rgba(34,197,94,0.15);">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" style="color:#22c55e;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <div>
            <p class="text-sm font-medium text-white">Stems exported</p>
            <p class="text-xs" style="color:#475569;">Vocals · Drums · Bass · Other</p>
          </div>
          <button @click="resetSplit"
            class="ml-auto text-xs px-3 py-1 rounded-lg transition-colors"
            style="color:#475569; border:1px solid rgba(255,255,255,0.08);"
            onmouseover="this.style.color='#94a3b8'" onmouseout="this.style.color='#475569'">
            Reset
          </button>
        </div>

        <!-- Controls -->
        <div v-else class="p-3 space-y-2">
          <div class="flex gap-2">
            <button @click="selectOutput"
              class="flex-1 text-sm py-2 rounded-lg transition-colors"
              :style="outputPath
                ? 'background:rgba(34,197,94,0.1);color:#22c55e;border:1px solid rgba(34,197,94,0.2);'
                : 'background:#1e293b;color:#94a3b8;border:1px solid rgba(255,255,255,0.06);'">
              {{ outputPath ? '✓ Output set' : 'Set output folder' }}
            </button>
            <button @click="split" :disabled="!songPath || !outputPath"
              class="flex-1 text-sm font-medium py-2 rounded-lg transition-all"
              style="background:linear-gradient(135deg,#16a34a,#15803d); color:white;"
              :style="(!songPath || !outputPath) ? 'opacity:0.35; cursor:not-allowed;' : 'opacity:1;'">
              Split Stems
            </button>
          </div>
          <p v-if="splitError" class="text-xs" style="color:#f87171;">{{ splitError }}</p>
        </div>
      </div>

      <!-- Error -->
      <div v-if="dnaError"
           class="rounded-xl p-3 text-xs"
           style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); color:#fca5a5;">
        {{ dnaError }}
      </div>

    </div>

    <!-- ── Bottom action bar ──────────────────────────────────────────────── -->
    <div class="shrink-0 px-4 py-3 flex gap-2"
         style="border-top:1px solid rgba(255,255,255,0.05); background:#0a0e17;">
      <button @click="selectSong"
        class="flex-1 text-sm font-medium py-2.5 rounded-xl transition-all active:scale-95"
        style="background:#1e293b; color:#94a3b8; border:1px solid rgba(255,255,255,0.06);"
        onmouseover="this.style.color='#e2e8f0';this.style.background='#263548'"
        onmouseout="this.style.color='#94a3b8';this.style.background='#1e293b'">
        {{ songPath ? 'Change Track' : '+ Load Track' }}
      </button>
      <button v-if="songPath && !isAnalyzing" @click="analyzeTrack"
        class="flex-1 text-sm font-medium py-2.5 rounded-xl transition-all active:scale-95"
        style="background:linear-gradient(135deg,#1d4ed8,#7c3aed); color:white; border:1px solid rgba(255,255,255,0.08);">
        Analyze DNA
      </button>
      <button v-if="isAnalyzing" disabled
        class="flex-1 text-sm font-medium py-2.5 rounded-xl"
        style="background:#1e293b; color:#475569; cursor:not-allowed;">
        Analyzing...
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
      isDragging:    false,
    }
  },

  computed: {},

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
    onDragOver(e) {
      const items = e.dataTransfer?.items
      if (!items) return
      for (const item of items) {
        if (item.kind === 'file') { this.isDragging = true; return }
      }
    },
    onDragLeave() { this.isDragging = false },
    onFileDrop(e) {
      this.isDragging = false
      const file = e.dataTransfer?.files?.[0]
      if (!file) return
      const ext = file.name.split('.').pop().toLowerCase()
      if (!['mp3', 'wav', 'flac', 'aiff', 'aif', 'm4a'].includes(ext)) return
      this.songPath   = file.path
      this.songName   = file.name.replace(/\.[^/.]+$/, '')
      this.dna        = null
      this.dnaError   = null
      this.splitError = null
      this.isDone     = false
    },

    async selectSong() {
      const p = await window.api.selectFile()
      if (!p) return
      // Full reset → back to initial state with new track loaded
      this.songPath    = p
      this.songName    = p.split('/').pop().replace(/\.[^/.]+$/, '')
      this.dna         = null
      this.dnaError    = null
      this.splitError  = null
      this.isDone      = false
      this.isAnalyzing = false
      this.dnaProgress = 0
      this.dnaStep     = ''
      this.splitProgress = 0
      this.isProcessing  = false
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
