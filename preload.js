const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("api", {

  selectFile: () => ipcRenderer.invoke("select-file"),

  selectOutput: () => ipcRenderer.invoke("select-output"),

  runDemucs: (input, output) =>
    ipcRenderer.invoke("run-demucs", input, output),

  readLogs: () => ipcRenderer.invoke("read-logs"),

  readLogFile: (filename) => ipcRenderer.invoke("read-log-file", filename),

  analyzeTrack: (audioFile) => ipcRenderer.invoke("analyze-track", audioFile),

  // Fires { pct: 0-100, step: string } during DNA analysis
  onDnaProgress: (cb) => ipcRenderer.on('dna-progress', (_e, data) => cb(data)),
  offDnaProgress: () => ipcRenderer.removeAllListeners('dna-progress'),

})