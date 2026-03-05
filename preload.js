const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("api", {

  selectFile: () => ipcRenderer.invoke("select-file"),

  selectOutput: () => ipcRenderer.invoke("select-output"),

  runDemucs: (input, output) =>
    ipcRenderer.invoke("run-demucs", input, output)

})