const { app, BrowserWindow, ipcMain, dialog } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const fs = require("fs")

let mainWindow

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const devPythonPath = path.join(__dirname, 'python_env', 'bin', 'python3')

const resourcesPath = isDev
  ? path.join(__dirname, 'python_binaries')
  : path.join(process.resourcesPath, 'python_binaries')

const logsDir = isDev
  ? path.join(__dirname, 'output')
  : path.join(app.getPath('userData'), 'output')

if (isDev) {
  console.log('[BLOND] dev mode | resources:', resourcesPath)
}

function getPythonScript(scriptName) {
  if (isDev) {
    return path.join(__dirname, 'demucs', `${scriptName}.py`)
  } else {
    return path.join(resourcesPath, scriptName, scriptName)
  }
}

function getPythonInterpreter() {
  return isDev ? devPythonPath : null
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 820,
    height: 640,
    minWidth: 700,
    minHeight: 580,
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.loadFile(path.join(__dirname, 'index.html'))
  if (isDev) mainWindow.webContents.openDevTools()
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

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
  try {
    if (!fs.existsSync(logsDir)) return []
    return fs.readdirSync(logsDir)
      .filter(f => f.startsWith('demucs_log'))
      .sort()
      .reverse()
  } catch {
    return []
  }
})

ipcMain.handle("read-log-file", async (event, filename) => {
  const filePath = path.join(logsDir, filename)
  try {
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return ''
  }
})

ipcMain.handle("run-demucs", async (event, inputFile, outputFolder) => {
  return new Promise((resolve, reject) => {
    const demucsRunnerPath = getPythonScript('demucs_runner')

    // Create logs dir and generate a unique log file path
    fs.mkdirSync(logsDir, { recursive: true })
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const logFile = path.join(logsDir, `demucs_log_${ts}.txt`)

    // Clean old log files
    try {
      fs.readdirSync(logsDir)
        .filter(f => f.startsWith('demucs_log'))
        .forEach(f => fs.unlinkSync(path.join(logsDir, f)))
    } catch (err) {
      console.error('[Electron] Error cleaning old logs:', err)
    }

    // Create empty log file so read-logs finds it immediately
    fs.writeFileSync(logFile, '')

    console.log('[Electron] Starting demucs:', demucsRunnerPath)
    console.log('[Electron] Input:', inputFile)
    console.log('[Electron] Output:', outputFolder)
    console.log('[Electron] Log:', logFile)

    // In dev: python3 demucs_runner.py <input> <output> <log>
    // In prod: ./demucs_runner <input> <output> <log>
    const pythonInterpreter = getPythonInterpreter()
    const args = isDev
      ? [demucsRunnerPath, inputFile, outputFolder, logFile]
      : [inputFile, outputFolder, logFile]
    const command = isDev ? pythonInterpreter : demucsRunnerPath

    const proc = spawn(command, args, {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let stderr = ''

    proc.stdout.on('data', (data) => {
      console.log('[Demucs stdout]:', data.toString())
    })

    proc.stderr.on('data', (data) => {
      stderr += data.toString()
      console.log('[Demucs stderr]:', data.toString())
    })

    proc.on('close', (code) => {
      console.log('[Electron] Demucs closed with code:', code)
      if (code === 0) {
        resolve({ code, logFile })
      } else {
        reject(new Error(`Demucs failed (code ${code})\n${stderr}`))
      }
    })

    proc.on('error', (err) => {
      console.error('[Electron] Demucs spawn error:', err)
      reject(err)
    })
  })
})

ipcMain.handle("detect-bpm", async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    const pythonInterpreter = getPythonInterpreter()
    const bpmDetectorPath = getPythonScript('bpm_detector')

    console.log('[Electron] Detecting BPM for:', audioFile)
    console.log('[Electron] Using:', isDev ? 'Python script' : 'Compiled binary')

    const args = isDev ? [bpmDetectorPath, audioFile] : [audioFile]
    const command = isDev ? pythonInterpreter : bpmDetectorPath

    const process = spawn(command, args, {
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
        const trimmed = output.trim()
        if (!trimmed) {
          console.error('[Electron] No output from BPM detector. Stderr:', stderr)
          reject(new Error('No output from BPM detector'))
          return
        }
        const result = JSON.parse(trimmed)
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

ipcMain.handle("detect-key", async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    const pythonInterpreter = getPythonInterpreter()
    const keyDetectorPath = getPythonScript('key_detector')

    console.log('[Electron] Detecting key for:', audioFile)
    console.log('[Electron] Using:', isDev ? 'Python script' : 'Compiled binary')

    const args = isDev ? [keyDetectorPath, audioFile] : [audioFile]
    const command = isDev ? pythonInterpreter : keyDetectorPath

    const process = spawn(command, args, {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let output = ''
    let stderr = ''

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    process.stderr.on('data', (data) => {
      stderr += data.toString()
      console.error('[Python Key stderr]:', data.toString())
    })

    process.on("close", (code) => {
      try {
        if (!output || output.trim() === '') {
          console.error('[Electron] No output from key detector. Stderr:', stderr)
          reject(new Error('No output from key detector - check logs'))
          return
        }
        
        const result = JSON.parse(output)
        console.log('[Electron] Key Detection Result:', result)
        
        if (!result.success) {
          reject(new Error(result.error || 'Key detection failed'))
        } else {
          resolve(result)
        }
      } catch (err) {
        console.error('[Electron] Error parsing key result. Output:', output, 'Error:', err)
        reject(new Error('Failed to detect key - invalid response'))
      }
    })

    process.on("error", (err) => {
      console.error('[Electron] Key Detection error:', err)
      reject(err)
    })
  })
})