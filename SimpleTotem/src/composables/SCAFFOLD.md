# Scaffold — composables/

Hooks **reutilizáveis** (Composition API).

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `useIdleTimer.js` | Timer de inatividade — redireciona para timeout |
| `useThermalPrinter.js` | Wrapper IPC para impressão térmica via Electron |
| `useCompanyInitialization.js` | Init da empresa na sessão (marca app como pronto) |

## Uso

Importar em views/layouts: `import { useIdleTimer } from '@/composables/useIdleTimer'`
