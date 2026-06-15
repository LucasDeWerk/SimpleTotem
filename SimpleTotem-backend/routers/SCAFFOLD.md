# Scaffold — routers/

Endpoints **REST** FastAPI. Routers finos — lógica pesada em `services/`.

## Arquivos

| Arquivo | Prefixo | Papel |
|---------|---------|-------|
| `auth.py` | `/auth` | Login JWT |
| `catalogo.py` | `/catalogo` | Grupos, subgrupos, produtos (leitura) |
| `empresa.py` | `/empresa` | Dados da empresa |
| `vendas.py` | `/vendas` | Carrinho, métodos pagamento, transação SiTef |
| `hardware.py` | `/hardware` | CPU/mem/disk + CRUD dispositivos USB |
| `sinc.py` | `/sinc` | Sync bidirecional com API externa |

## Auth

Rotas protegidas usam `Depends(get_current_user)` de `core/security.py`.

## Registro

Todos incluídos em `app.py` via `app.include_router()`.
