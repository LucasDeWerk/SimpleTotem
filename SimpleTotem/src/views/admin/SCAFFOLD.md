# Scaffold — views/admin/

Telas **administrativas** — sync de dados e config de hardware.

## Arquivos

| Arquivo | Rota | Papel |
|---------|------|-------|
| `AdminLoginView.vue` | `/admin` | Login admin (localStorage) |
| `AdminPanelView.vue` | `/admin/painel` | Sync de catálogo/empresa com API externa |
| `AdminHardwareView.vue` | `/admin/hardware` | Configuração de impressora USB (VID/PID) |

## Auth

Guard em `router/index.js` — rotas com `requiresAdmin` checam `localStorage.admin_authenticated`.

## Stores / services

`admin` store, `api.js` (sync + hardware)
