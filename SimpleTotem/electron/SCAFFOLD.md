# Scaffold — electron/

**Main process** do Electron — hardware local (USB, impressora). Sem SQLite.

Contexto geral: [.cursor/cursor.md](../../.cursor/cursor.md)

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `main.js` | Janela kiosk, IPC handlers, listagem USB via sysfs |
| `preload.js` | Bridge seguro: expõe `electronAPI` e `hardwareAPI` ao renderer |
| `printer.js` | Impressão térmica escpos-usb; busca config no backend `:8000` |

## IPC exposto (preload → renderer)

| Canal | Função |
|-------|--------|
| `hardware:listar-usb` | Lista dispositivos USB via `/sys/bus/usb/devices` |
| `printer:print-lines` | Imprime linhas de texto na térmica |
| `printer:print-raw` | Envia buffer raw para impressora |
| `printer:test-print` | Impressão de teste |
| `toggle-fullscreen` | Alterna fullscreen |

## Regras

- Config de impressora vem do backend (`GET /hardware/dispositivos`)
- Nunca abrir/gravar SQLite aqui

## Agente

Tarefas aqui → **frontend-agent**
