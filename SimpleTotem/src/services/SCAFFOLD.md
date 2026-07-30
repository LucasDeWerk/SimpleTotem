# Scaffold — services/

Camada de **comunicação HTTP** com o backend FastAPI.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `api.js` | Cliente REST — JWT, catálogo, vendas, hardware, sync |

## Endpoints principais (via api.js)

| Função | Endpoint |
|--------|----------|
| `obterGrupos()` | `GET /catalogo/grupos` |
| `obterProdutos()` | `GET /catalogo/produtos` |
| `iniciarVenda()` | `POST /vendas/iniciavenda` |
| `iniciarTransacao()` | `POST /vendas/iniciatransacao` |
| `obterConfigHardware()` | `GET /hardware/dispositivos` |
| `listarDispositivosUSB()` | IPC local (Electron), não vai ao backend |

Base URL: `localStorage.api_base_url` ou `http://localhost:8000`

## Regra

Novo endpoint no backend → adicionar função aqui antes de usar nas stores/views.
