# SimpleTotem

Totem de autoatendimento — Vue 3 + Electron + FastAPI + CliSiTef.

## Documentação para o Cursor

| Arquivo | Conteúdo |
|---------|----------|
| [.cursor/cursor.md](.cursor/cursor.md) | Visão geral, arquitetura, como rodar |
| [.cursor/agents/](.cursor/agents/) | Subagents (frontend, frontend-bug, backend, orchestrator, ux-ui-review) |
| **SCAFFOLD.md** em cada pasta | Mapa de arquivos e responsabilidades |

O Cursor indexa `README.md` e `SCAFFOLD.md` quando não estão no `.cursorignore`. Use `@SCAFFOLD.md` ou `@README.md` no chat para forçar o contexto.

## Estrutura

```
SimpleTotem/           → Frontend (ver SCAFFOLD.md)
SimpleTotem-backend/   → Backend  (ver SCAFFOLD.md)
script/                → CliSiTef   (ver SCAFFOLD.md)
dados/                 → SQLite runtime (não versionado)
```

## Pinpad (instalação única no totem)

```bash
sudo bash script/instalar_permissoes_totem.sh
```

Configura udev, sudo sem senha para o SiTef e porta do pinpad no `CliSiTef.ini`. Depois disso o backend acessa o pinpad automaticamente (como root, sem pedir senha).

## Início rápido

```bash
# Backend
cd SimpleTotem-backend && source .venv/bin/activate && python main.py

# Frontend
cd SimpleTotem && npm run electron:dev
```
