"use strict";
const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const fs   = require("fs");
const Database = require("better-sqlite3");
require("usb");
const { setupPrinterIPC } = require("./printer");
let mainWindow = null;
let db = null;
function getDbPath() {
  if (process.env.VITE_DEV_SERVER_URL) {
    return path.join(__dirname, "..", "..", "simplebd");
  }
  return path.join(app.getPath("userData"), "simplebd");
}
function openDatabase() {
  if (db) return db;
  const dbPath = getDbPath();
  console.log("[Database] Abrindo banco em:", dbPath);
  try {
    db = new Database(dbPath, { readonly: false });
    db.pragma("journal_mode = WAL");
    db.pragma("foreign_keys = ON");
    console.log("[Database] Banco aberto com sucesso");
  } catch (err) {
    console.error("[Database] Erro ao abrir banco:", err.message);
    throw err;
  }
  return db;
}
function closeDatabase() {
  if (db) { db.close(); db = null; console.log("[Database] Banco fechado"); }
}
function getDb() {
  if (!db) openDatabase();
  return db;
}
function getGrupos() { return []; }
function getSubgrupos() { return []; }
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
function getSiTefConfig() {}
app.whenReady().then(() => {
   // Banco aberto apenas para uso interno (printer)
   try {
     openDatabase();
     console.log("[Main] Banco de dados conectado (uso interno)");
   } catch (err) {
     console.error("[Main] Erro ao conectar banco:", err.message);
   }
   setupPrinterIPC();
   ipcMain.handle("hardware:listar-usb", () => listarUSBViaSysfs());
   ipcMain.handle("toggle-fullscreen", () => {
     if (mainWindow) {
       mainWindow.setFullScreen(!mainWindow.isFullScreen());
     }
     return true;
   });
   createWindow();
});
app.on("window-all-closed", () => {
  closeDatabase();
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
