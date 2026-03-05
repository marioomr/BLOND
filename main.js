const { app, BrowserWindow, ipcMain, dialog } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const fs = require("fs")

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
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle("select-output", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"]
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle("read-logs", async () => {
  const outputDir = path.join(__dirname, 'output')
  try {
    if (!fs.existsSync(outputDir)) return []
    return fs.readdirSync(outputDir)
      .filter(f => f.startsWith('demucs_log'))
      .sort()
      .reverse()
  } catch {
    return []
  }
})

ipcMain.handle("read-log-file", async (event, filename) => {
  const filePath = path.join(__dirname, 'output', filename)
  try {
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return ''
  }
})

ipcMain.handle("run-demucs", async (event, inputFile, outputFolder) => {
  return new Promise((resolve, reject) => {
    const pythonPath = path.join(__dirname, 'python_env', 'bin', 'python3')
    const demucsRunnerPath = path.join(__dirname, 'demucs', 'demucs_runner.py')
    const outputDir = path.join(__dirname, 'output')

    console.log('[Electron] Starting demucs process...')
    console.log('[Electron] Python:', pythonPath)
    console.log('[Electron] Script:', demucsRunnerPath)
    console.log('[Electron] Input:', inputFile)
    console.log('[Electron] Output:', outputFolder)

    // Clean old logs before starting new process
    try {
      if (fs.existsSync(outputDir)) {
        const files = fs.readdirSync(outputDir)
        files.forEach(f => {
          if (f.startsWith('demucs_log')) {
            fs.unlinkSync(path.join(outputDir, f))
          }
        })
      }
    } catch (err) {
      console.error('[Electron] Error cleaning old logs:', err)
    }

    const process = spawn(pythonPath, [demucsRunnerPath, inputFile, outputFolder], {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let stdout = ''
    let stderr = ''

    process.stdout.on('data', (data) => {
      stdout += data.toString()
      console.log('[Python stdout]:', data.toString())
    })

    process.stderr.on('data', (data) => {
      stderr += data.toString()
      console.log('[Python stderr]:', data.toString())
    })

    process.on("close", (code) => {
      console.log('[Electron] Process closed with code:', code)
      if (code === 0) {
        resolve({ code, stdout, stderr })
      } else {
        reject(new Error(`Process exited with code ${code}\n${stderr}`))
      }
    })

    process.on("error", (err) => {
      console.error('[Electron] Process error:', err)
      reject(err)
    })
  })
})

ipcMain.handle("detect-bpm", async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    const pythonPath = path.join(__dirname, 'python_env', 'bin', 'python3')
    const bpmDetectorPath = path.join(__dirname, 'demucs', 'bpm_detector.py')

    console.log('[Electron] Detecting BPM for:', audioFile)

    const process = spawn(pythonPath, [bpmDetectorPath, audioFile], {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let output = ''
    let stderr = ''

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    process.stderr.on('data', (data) => {
      stderr += data.toString()
      console.error('[Python BPM stderr]:', data.toString())
    })

    process.on("close", (code) => {
      try {
        const result = JSON.parse(output)
        console.log('[Electron] BPM Detection Result:', result)
        resolve(result)
      } catch (err) {
        console.error('[Electron] Error parsing BPM result:', err)
        reject(new Error('Failed to detect BPM'))
      }
    })

    process.on("error", (err) => {
      console.error('[Electron] BPM Detection error:', err)
      reject(err)
    })
  })
})