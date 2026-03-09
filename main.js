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

// Logs base dir — subcarpeta por módulo
const logsBaseDir = isDev
  ? path.join(__dirname, 'logs')
  : path.join(app.getPath('userData'), 'logs')

const logsDir = path.join(logsBaseDir, 'demucs')    // legacy compat
const dnalogsDir = path.join(logsBaseDir, 'dna')

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true })
}

if (isDev) {
  console.log('[BLOND] dev mode | resources:', resourcesPath)
  console.log('[BLOND] logs:', logsBaseDir)
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
      .filter(f => f.startsWith('demucs_log') && f.endsWith('.txt'))
      .sort()
      .reverse()
  } catch {
    return []
  }
})

ipcMain.handle("read-log-file", async (event, filename) => {
  // Support both demucs and dna logs by subfolder prefix
  let filePath
  if (filename.startsWith('dna_')) {
    filePath = path.join(dnalogsDir, filename)
  } else {
    filePath = path.join(logsDir, filename)
  }
  try {
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return ''
  }
})

ipcMain.handle("run-demucs", async (event, inputFile, outputFolder) => {
  return new Promise((resolve, reject) => {
    const demucsRunnerPath = getPythonScript('demucs_runner')

    ensureDir(logsDir)
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const logFile = path.join(logsDir, `demucs_log_${ts}.txt`)

    // Clean old demucs logs (keep last 5)
    try {
      const old = fs.readdirSync(logsDir)
        .filter(f => f.startsWith('demucs_log') && f.endsWith('.txt'))
        .sort()
      old.slice(0, Math.max(0, old.length - 5))
        .forEach(f => fs.unlinkSync(path.join(logsDir, f)))
    } catch (err) {
      console.error('[Electron] Error cleaning old demucs logs:', err)
    }

    fs.writeFileSync(logFile, `[${new Date().toISOString()}] Starting demucs\nInput: ${inputFile}\nOutput: ${outputFolder}\n`)

    console.log('[Electron] Starting demucs:', demucsRunnerPath)

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
      const line = data.toString()
      fs.appendFileSync(logFile, `[stdout] ${line}`)
      console.log('[Demucs stdout]:', line)
    })

    proc.stderr.on('data', (data) => {
      const line = data.toString()
      stderr += line
      fs.appendFileSync(logFile, line)
      console.log('[Demucs stderr]:', line)
    })

    proc.on('close', (code) => {
      fs.appendFileSync(logFile, `\n[EXIT CODE] ${code}\n`)
      console.log('[Electron] Demucs closed with code:', code)
      if (code === 0) {
        resolve({ code, logFile })
      } else {
        reject(new Error(`Demucs failed (code ${code})\n${stderr}`))
      }
    })

    proc.on('error', (err) => {
      fs.appendFileSync(logFile, `\n[SPAWN ERROR] ${err.message}\n`)
      console.error('[Electron] Demucs spawn error:', err)
      reject(err)
    })
  })
})

ipcMain.handle("analyze-track", async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    const pythonInterpreter = getPythonInterpreter()
    const trackDnaPath = getPythonScript('track_dna')

    ensureDir(dnalogsDir)
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const logFile = path.join(dnalogsDir, `dna_log_${ts}.txt`)

    // Keep last 10 dna logs
    try {
      const old = fs.readdirSync(dnalogsDir)
        .filter(f => f.startsWith('dna_log') && f.endsWith('.txt'))
        .sort()
      old.slice(0, Math.max(0, old.length - 10))
        .forEach(f => fs.unlinkSync(path.join(dnalogsDir, f)))
    } catch {}

    fs.writeFileSync(logFile, `[${new Date().toISOString()}] Track DNA analysis started\nFile: ${audioFile}\n`)

    console.log('[Electron] Analyzing track DNA:', audioFile)

    const args = isDev ? [trackDnaPath, audioFile] : [audioFile]
    const command = isDev ? pythonInterpreter : trackDnaPath

    const proc = spawn(command, args, {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let output = ''
    let stderr = ''

    proc.stdout.on('data', (data) => {
      output += data.toString()
    })

    proc.stderr.on('data', (data) => {
      const chunk = data.toString()
      stderr += chunk
      fs.appendFileSync(logFile, chunk)

      // Parse PROGRESS lines and forward to renderer
      chunk.split('\n').forEach(line => {
        const m = line.match(/^PROGRESS:(\d+)(?:\s+(.+))?/)
        if (m) {
          const pct = parseInt(m[1])
          const step = m[2] || ''
          console.log(`[DNA] ${pct}% ${step}`)
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('dna-progress', { pct, step })
          }
        } else if (line.includes('[track_dna]')) {
          console.log(line)
        }
      })
    })

    proc.on('close', (code) => {
      fs.appendFileSync(logFile, `\n[EXIT CODE] ${code}\n`)
      try {
        const trimmed = output.trim()
        if (!trimmed) {
          fs.appendFileSync(logFile, '[ERROR] No stdout output\n')
          reject(new Error('No output from track_dna'))
          return
        }
        const result = JSON.parse(trimmed)
        fs.appendFileSync(logFile, `[RESULT] BPM=${result.bpm} Key=${result.key} Energy=${result.energy}\n`)
        console.log('[Electron] DNA done — BPM:', result.bpm, '| Key:', result.key)
        resolve(result)
      } catch (err) {
        fs.appendFileSync(logFile, `[PARSE ERROR] ${err.message}\nOutput: ${output.slice(0, 500)}\n`)
        reject(new Error('Failed to parse track_dna output'))
      }
    })

    proc.on('error', (err) => {
      fs.appendFileSync(logFile, `[SPAWN ERROR] ${err.message}\n`)
      reject(err)
    })
  })
})