"use strict";
const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const fs   = require("fs");
const os   = require("os");
require("usb");
const { setupPrinterIPC } = require("./printer");
let mainWindow = null;
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
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
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
app.whenReady().then(() => {
   setupPrinterIPC();
   ipcMain.handle("hardware:listar-usb", () => listarUSBViaSysfs());
   ipcMain.handle("toggle-fullscreen", () => {
     if (mainWindow) {
       mainWindow.setFullScreen(!mainWindow.isFullScreen());
     }
     return true;
   });
   ipcMain.handle("get-system-user", () => {
     try {
       return os.userInfo().username || null;
     } catch (_) {
       return null;
     }
   });
   createWindow();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
