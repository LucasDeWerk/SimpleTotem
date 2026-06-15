# Scaffold — SimpleTotem/ (Frontend)

App **Vue 3 + Electron** do totem. Sem acesso a banco — consome API em `:8000`.

Contexto geral: [.cursor/cursor.md](../.cursor/cursor.md)

## Subpastas

| Pasta | Scaffold |
|-------|----------|
| `src/` | [src/SCAFFOLD.md](src/SCAFFOLD.md) |
| `electron/` | [electron/SCAFFOLD.md](electron/SCAFFOLD.md) |

## Arquivos (raiz)

| Arquivo | Papel |
|---------|-------|
| `package.json` | Dependências, scripts npm (dev, electron:dev, build) |
| `vite.config.js` | Vite + vite-plugin-electron, aliases, build |
| `copy-electron-files.js` | Copia auxiliares electron/ → dist-electron/ pós-build |
| `index.html` | Entry HTML do Vite |
| `.env.example` | Exemplo de variáveis (referência) |
| `.gitignore` | Ignorados locais do frontend |

## Comandos

```bash
npm install
npm run dev              # só Vite
npm run electron:dev     # Vite + Electron
npm run build            # build produção
```

## Agente

Tarefas aqui → **frontend-agent**
