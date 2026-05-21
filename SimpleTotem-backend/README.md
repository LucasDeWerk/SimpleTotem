# Hardware API — SimpleTotem Backend

Backend local em FastAPI com autenticação JWT para controle e monitoramento de hardware.

## Estrutura

```
├── main.py                  # Entry point (uvicorn programático)
├── app.py                   # Instância FastAPI + registro de routers
├── requirements.txt
├── core/
│   ├── config.py            # SECRET_KEY, ALGORITHM, credenciais admin
│   └── security.py          # JWT: geração, validação, dependency injection
├── models/
│   └── schemas.py           # Pydantic models (LoginRequest, TokenResponse, CPUInfo, ...)
├── routers/
│   ├── auth.py              # POST /auth/login
│   └── hardware.py          # GET /hardware/cpu | /memory | /disk  (protegidas por JWT)
└── services/
    └── hardware_service.py  # Leitura de hardware via psutil
```

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

API disponível em: http://127.0.0.1:8000  
Docs interativas: http://127.0.0.1:8000/docs

## Autenticação

1. `POST /auth/login` com `{ "username": "admin", "password": "admin123" }`
2. Use o `access_token` retornado no header: `Authorization: Bearer <token>`

## Build com PyInstaller

```bash
pyinstaller --onefile main.py \
  --hidden-import=uvicorn.logging \
  --hidden-import=uvicorn.loops \
  --hidden-import=uvicorn.loops.auto \
  --hidden-import=uvicorn.protocols \
  --hidden-import=uvicorn.protocols.http \
  --hidden-import=uvicorn.protocols.http.auto \
  --hidden-import=uvicorn.protocols.websockets \
  --hidden-import=uvicorn.protocols.websockets.auto \
  --hidden-import=uvicorn.lifespan \
  --hidden-import=uvicorn.lifespan.on
```

> `reload=False` é obrigatório para compatibilidade com PyInstaller.

