"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  getDeviceId:    () => ipcRenderer.invoke("get-device-id"),
  getAppVersion:  () => ipcRenderer.invoke("get-app-version"),
  getSystemUser:  () => ipcRenderer.invoke("get-system-user"),
  toggleKiosk:    () => ipcRenderer.invoke("toggle-kiosk"),
  toggleFullscreen: () => ipcRenderer.invoke("toggle-fullscreen"),
  quit:           () => ipcRenderer.invoke("quit-app"),
  platform: process.platform,
  printer: {
    // Clona args via JSON para evitar DataCloneError com proxies Vue no IPC,
    // preservando linhas como string OU { text, bold } (String(obj) virava "[object Object]")
    printLines: (lines, options) =>
      ipcRenderer.invoke(
        "printer:print-lines",
        Array.isArray(lines) ? JSON.parse(JSON.stringify(lines)) : [],
        options && typeof options === "object" ? JSON.parse(JSON.stringify(options)) : {}
      ),
    printRaw: (bufferData) =>
      ipcRenderer.invoke(
        "printer:print-raw",
        Array.isArray(bufferData) ? [...bufferData] : Array.from(bufferData || [])
      ),
    testPrint: () => ipcRenderer.invoke("printer:test-print")
  }
});

// Listagem de USB via sysfs (leitura local, sem banco de dados)
contextBridge.exposeInMainWorld("hardwareAPI", {
  listarUSB: () => ipcRenderer.invoke("hardware:listar-usb")
});

