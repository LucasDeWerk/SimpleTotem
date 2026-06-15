# Scaffold — services/

**Lógica de negócio** do backend — isolada dos routers.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `hardware_service.py` | Leitura de CPU/memória/disco via psutil |
| `sitef_service.py` | Orquestração CliSiTef — interface de alto nível |
| `sitef_worker.py` | Loop de interação com pinpad (campos TC, cupom) |

## Integração CliSiTef

Libs em `../../script/*.so`, config em `../../script/CliSiTef.ini`.

Fluxo de pagamento: `vendas.py` → `sitef_service` → `sitef_worker` → lib nativa.

## Regra

Routers não devem conter lógica SiTef ou psutil diretamente.
