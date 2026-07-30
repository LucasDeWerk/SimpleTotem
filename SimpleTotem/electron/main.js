"use strict";
const { app, BrowserWindow, ipcMain, globalShortcut } = require("electron");
const { spawn } = require("child_process");
const http  = require("http");
const path  = require("path");
const fs    = require("fs");
const os    = require("os");
require("usb");
const { setupPrinterIPC } = require("./printer");

let mainWindow     = null;
let backendProcess = null;

// ── Backend spawn (somente em produção) ──────────────────────────────────────

function findBackendBinary() {
  const candidates = [];

  if (process.env.APPIMAGE) {
    // AppImage: $APPIMAGE aponta para o arquivo .AppImage; backend fica ao lado
    candidates.push(path.join(path.dirname(process.env.APPIMAGE), "SimpleTotem-backend"));
  } else if (app.isPackaged) {
    // linux-unpacked: execPath = <install>/SimpleTotem/simple-totem
    // backend fica um nível acima: <install>/SimpleTotem-backend
    candidates.push(path.join(path.dirname(process.execPath), "SimpleTotem-backend"));
    candidates.push(path.join(path.dirname(process.execPath), "..", "SimpleTotem-backend"));
  }

  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null; // dev — backend iniciado separadamente
}

function waitForBackend(timeoutMs = 15000) {
  return new Promise((resolve) => {
    const deadline = Date.now() + timeoutMs;
    function attempt() {
      if (Date.now() > deadline) { resolve(false); return; }
      http.get("http://localhost:8000/empresa/status", (res) => {
        res.resume(); // drena a resposta
        resolve(true);
      }).on("error", () => setTimeout(attempt, 400));
    }
    attempt();
  });
}

async function startBackend() {
  // Se o backend já está respondendo (iniciado pelo launcher), não spawna de novo
  const alreadyUp = await waitForBackend(2000);
  if (alreadyUp) {
    console.log("[electron] Backend já está rodando (modo launcher)");
    return;
  }

  const binPath = findBackendBinary();
  if (!binPath) {
    console.log("[electron] Modo dev — backend não iniciado pelo Electron");
    return;
  }

  console.log("[electron] Iniciando backend:", binPath);
  backendProcess = spawn(binPath, [], {
    detached: false,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProcess.stdout.on("data", (d) => process.stdout.write(`[backend] ${d}`));
  backendProcess.stderr.on("data", (d) => process.stderr.write(`[backend] ${d}`));
  backendProcess.on("exit", (code) => {
    console.log(`[electron] Backend encerrou (código ${code})`);
    backendProcess = null;
  });

  const ok = await waitForBackend();
  if (ok) {
    console.log("[electron] Backend pronto");
  } else {
    console.warn("[electron] Backend não respondeu em 15s — carregando mesmo assim");
  }
}
function createWindow() {
   mainWindow = new BrowserWindow({
     width: 1080, height: 1920,
     fullscreen: true, frame: true, kiosk: false, autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  const openDevTools = () => {
    if (!mainWindow?.webContents.isDevToolsOpened()) {
      mainWindow.webContents.openDevTools({ mode: "detach" });
    }
  };

  if (!app.isPackaged || process.env.VITE_DEV_SERVER_URL) {
    mainWindow.webContents.once("did-finish-load", openDevTools);
  }

  mainWindow.webContents.on("before-input-event", (_event, input) => {
    if (input.key === "F12" || (input.control && input.shift && input.key.toLowerCase() === "i")) {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
      } else {
        openDevTools();
      }
    }
  });
  mainWindow.on("closed", () => { mainWindow = null; });
}
function listarUSBViaSysfs() {
  const basePath = "/sys/bus/usb/devices";
  const resultado = [];
  let entries;
  try { entries = fs.readdirSync(basePath); } catch (_) { return resultado; }
  for (const entry of entries) {
    const devicePath = path.join(basePath, entry);
    try {
      const vPath = path.join(devicePath, "idVendor");
      const pPath = path.join(devicePath, "idProduct");
      if (!fs.existsSync(vPath) || !fs.existsSync(pPath)) continue;
      const vid = fs.readFileSync(vPath, "utf8").trim();
      const pid = fs.readFileSync(pPath, "utf8").trim();
      let fabricante = "Desconhecido", produto = "USB " + vid + ":" + pid;
      const mPath = path.join(devicePath, "manufacturer");
      const prPath = path.join(devicePath, "product");
      if (fs.existsSync(mPath))  fabricante = fs.readFileSync(mPath,  "utf8").trim();
      if (fs.existsSync(prPath)) produto    = fs.readFileSync(prPath, "utf8").trim();
      resultado.push({ vendorId: vid, productId: pid, fabricante, produto });
    } catch (_) {}
  }
  return resultado;
}
app.whenReady().then(async () => {
  setupPrinterIPC();
  ipcMain.handle("hardware:listar-usb", () => listarUSBViaSysfs());
  ipcMain.handle("toggle-fullscreen", () => {
    if (mainWindow) mainWindow.setFullScreen(!mainWindow.isFullScreen());
    return true;
  });
  ipcMain.handle("get-system-user", () => {
    try { return os.userInfo().username || null; } catch (_) { return null; }
  });

  await startBackend();
  createWindow();
});

app.on("before-quit", () => {
  if (backendProcess) {
    console.log("[electron] Encerrando backend...");
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
});

app.on("window-all-closed", () => {
  globalShortcut.unregisterAll();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
