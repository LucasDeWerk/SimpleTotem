/**
 * copy-electron-files.js
 * Copia arquivos auxiliares do Electron para dist-electron/ após o build do Vite.
 * Chamado por: npm run dev (vite && node copy-electron-files.js)
 */

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, 'electron');
const DEST = path.join(__dirname, 'dist-electron');

// Arquivos a copiar de electron/ → dist-electron/
const FILES = [
  'printer.js',
  'sitef-node.js',
  'sitef-child.js',
];

// Copiar assets também
const ASSETS_SRC  = path.join(__dirname, 'dist-electron', 'assets');
const ASSETS_ORIG = path.join(__dirname, 'electron', 'assets');

if (!fs.existsSync(DEST)) {
  fs.mkdirSync(DEST, { recursive: true });
}

let copiados = 0;
let ignorados = 0;

for (const file of FILES) {
  const src  = path.join(SRC, file);
  const dest = path.join(DEST, file);

  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`[Copy] ✅ ${file}`);
    copiados++;
  } else {
    // Tentar pegar do dist-electron original (caso exista backup)
    console.log(`[Copy] ⚠️  ${file} não encontrado em electron/ — ignorando`);
    ignorados++;
  }
}

// Copiar pasta assets se existir
if (fs.existsSync(ASSETS_ORIG) && !fs.existsSync(ASSETS_SRC)) {
  fs.mkdirSync(ASSETS_SRC, { recursive: true });
  for (const asset of fs.readdirSync(ASSETS_ORIG)) {
    fs.copyFileSync(
      path.join(ASSETS_ORIG, asset),
      path.join(ASSETS_SRC, asset)
    );
    console.log(`[Copy] ✅ assets/${asset}`);
  }
}

console.log(`\n[Copy] Concluído: ${copiados} copiados, ${ignorados} ignorados`);

