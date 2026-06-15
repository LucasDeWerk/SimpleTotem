# Scaffold — core/

Infraestrutura central do backend — config, DB, auth, tokens.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `config.py` | SECRET_KEY, JWT, DB_PATH, URLs API externa |
| `database.py` | SQLAlchemy engine, SessionLocal, `get_db()` dependency |
| `security.py` | JWT — geração, validação, `get_current_user` |
| `token_cache.py` | Cache do token da API externa de sync (lifespan startup) |

## Variáveis de ambiente

`URL_API` — base da API SimpleSfique (login + sync), via `.env`

## Regras

- Secrets nunca hardcoded em produção
- `DB_PATH` → `dados/simplebd` (fora desta pasta)
