const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("api", {

  selectFile: () => ipcRenderer.invoke("select-file"),

  selectOutput: () => ipcRenderer.invoke("select-output"),

  runDemucs: (input, output) =>
    ipcRenderer.invoke("run-demucs", input, output),

  readLogs: () => ipcRenderer.invoke("read-logs"),

  readLogFile: (filename) => ipcRenderer.invoke("read-log-file", filename),

  detectBPM: (audioFile) => ipcRenderer.invoke("detect-bpm", audioFile),

  detectKey: (audioFile) => ipcRenderer.invoke("detect-key", audioFile)

})