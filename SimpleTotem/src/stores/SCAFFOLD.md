# Scaffold — stores/

Estado global **Pinia**. Cada store = um domínio do totem.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `catalog.js` | Grupos, subgrupos, produtos — carrega via `api.js` |
| `cart.js` | Itens do carrinho, totais, add/remove |
| `payment.js` | Métodos de pagamento, fluxo de transação |
| `session.js` | Sessão do cliente, idle timer |
| `admin.js` | Sync admin, status de sincronização |
| `device.js` | Info do dispositivo totem |
| `language.js` | Idioma/traduções da UI |

## Padrão

Stores chamam `services/api.js` — nunca acessam banco diretamente.
