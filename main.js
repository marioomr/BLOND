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

    let output = ""
    let error = ""

    pythonProcess.stdout.on("data", (data) => {
      const message = data.toString()
      console.log(message)
      output += message
    })

    pythonProcess.stderr.on("data", (data) => {
      const message = data.toString()
      console.error(message)
      error += message
    })

    pythonProcess.on("error", (err) => {
      console.error("Process error:", err)
      reject(err)
    })

    pythonProcess.on("close", (code) => {
      if (code === 0) {
        resolve({ success: true, output })
      } else {
        reject(new Error(`Python process exited with code ${code}: ${error}`))
      }
    })

  })

})