import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import { resolve, join } from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

// Plugin que copia arquivos auxiliares do Electron após cada build
function copyElectronAuxFiles() {
  const srcDir = join(__dirname, 'electron')
  const destDir = join(__dirname, 'dist-electron')

  const FILES = [
    'printer.js',
    'sitef-file-handler.js',
  ]

  return {
    name: 'copy-electron-aux-files',
    closeBundle() {
      if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true })
      for (const file of FILES) {
        const src = join(srcDir, file)
        const dest = join(destDir, file)
        if (fs.existsSync(src)) {
          fs.copyFileSync(src, dest)
        }
      }
      // Copiar assets
      const assetsSrc = join(srcDir, 'assets')
      const assetsDest = join(destDir, 'assets')
      if (fs.existsSync(assetsSrc)) {
        if (!fs.existsSync(assetsDest)) fs.mkdirSync(assetsDest, { recursive: true })
        for (const asset of fs.readdirSync(assetsSrc)) {
          fs.copyFileSync(join(assetsSrc, asset), join(assetsDest, asset))
        }
      }
    }
  }
}

export default defineConfig({
  plugins: [
    vue(),
    electron([
      {
        entry: 'electron/main.js',
        vite: {
          build: {
            outDir: 'dist-electron',
            rollupOptions: {
              external: ['electron', 'better-sqlite3', 'escpos', 'usb', 'jimp']
            }
          },
          plugins: [copyElectronAuxFiles()]
        }
      },
      {
        entry: 'electron/preload.js',
        onstart(args) {
          args.reload()
        },
        vite: {
          build: {
            outDir: 'dist-electron',
            rollupOptions: {
              external: ['electron']
            }
          }
        }
      }
    ]),
    renderer()
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173
  }
})
