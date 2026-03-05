const { app, BrowserWindow, ipcMain, dialog } = require("electron")
const path = require("path")
const { spawn } = require("child_process")

let mainWindow

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, "preload.js")
    }
  })

  mainWindow.loadFile("index.html")
}

app.whenReady().then(createWindow)

ipcMain.handle("select-file", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openFile"],
    filters: [{ name: "Audio", extensions: ["mp3", "wav"] }]
  })

  if (result.canceled) return null
  return result.filePaths[0]
})

ipcMain.handle("select-output", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"]
  })

  if (result.canceled) return null
  return result.filePaths[0]
})

ipcMain.handle("run-demucs", async (event, inputFile, outputFolder) => {

  return new Promise((resolve, reject) => {

    const pythonProcess = spawn(
      path.join(__dirname, "python_env/bin/python"),
      [
        path.join(__dirname, "demucs/demucs_runner.py"),
        inputFile,
        outputFolder
      ]
    )

    pythonProcess.stdout.on("data", (data) => {
      console.log(data.toString())
    })

    pythonProcess.stderr.on("data", (data) => {
      console.error(data.toString())
    })

    pythonProcess.on("close", (code) => {
      resolve(code)
    })

  })

})