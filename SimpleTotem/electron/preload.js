"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  getDeviceId:    () => ipcRenderer.invoke("get-device-id"),
  getAppVersion:  () => ipcRenderer.invoke("get-app-version"),
  toggleKiosk:    () => ipcRenderer.invoke("toggle-kiosk"),
  toggleFullscreen: () => ipcRenderer.invoke("toggle-fullscreen"),
  quit:           () => ipcRenderer.invoke("quit-app"),
  platform: process.platform,
  printer: {
    printLines: (lines, options) => ipcRenderer.invoke("printer:print-lines", lines, options),
    printRaw:   (bufferData)     => ipcRenderer.invoke("printer:print-raw", bufferData),
    testPrint:  ()               => ipcRenderer.invoke("printer:test-print")
  }
});

// Listagem de USB via sysfs (leitura local, sem banco de dados)
contextBridge.exposeInMainWorld("hardwareAPI", {
  listarUSB: () => ipcRenderer.invoke("hardware:listar-usb")
});

