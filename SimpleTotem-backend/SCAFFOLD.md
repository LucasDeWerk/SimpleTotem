# Scaffold — SimpleTotem-backend/

API **FastAPI** local — catálogo, vendas, hardware, sync, CliSiTef.

Contexto geral: [.cursor/cursor.md](../.cursor/cursor.md)  
Docs interativas: http://127.0.0.1:8000/docs

## Subpastas

| Pasta | Scaffold |
|-------|----------|
| `core/` | [core/SCAFFOLD.md](core/SCAFFOLD.md) |
| `models/` | [models/SCAFFOLD.md](models/SCAFFOLD.md) |
| `routers/` | [routers/SCAFFOLD.md](routers/SCAFFOLD.md) |
| `services/` | [services/SCAFFOLD.md](services/SCAFFOLD.md) |

## Arquivos (raiz)

| Arquivo | Papel |
|---------|-------|
| `main.py` | Entry point — uvicorn em `:8000`, `reload=False` |
| `app.py` | Instância FastAPI, CORS, registro de routers, lifespan |
| `requirements.txt` | Dependências Python |
| `README.md` | Documentação de instalação e build PyInstaller |

## Banco

SQLite em `../dados/simplebd` — configurado em `core/config.py`

## Comandos

```bash
source .venv/bin/activate
python main.py
```

## Agente

Tarefas aqui → **backend-agent**
