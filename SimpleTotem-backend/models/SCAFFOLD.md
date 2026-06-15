# Scaffold — models/

**ORM** (SQLAlchemy) e **schemas** (Pydantic).

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `orm.py` | Models SQLAlchemy — Empresa, Grupo, Produto, Venda, Hardware, etc. |
| `schemas.py` | Pydantic — request/response DTOs para routers |

## Padrão

- Tabelas espelham sync da API externa (`test_*`, `vstb_*`)
- Router recebe/retorna `schemas.py`; persiste via `orm.py`

## Ao adicionar entidade

1. Model em `orm.py`
2. Schemas In/Out em `schemas.py`
3. Router + service
