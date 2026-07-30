# Scaffold — views/cliente/

Telas do **fluxo do totem** (autoatendimento). Rota base: `/totem/*`.

## Arquivos

| Arquivo | Rota | Papel |
|---------|------|-------|
| `HomeView.vue` | `/totem` | Tela inicial — boas-vindas, início do fluxo |
| `CatalogView.vue` | `/totem/catalogo` | Catálogo principal (grupos → produtos) |
| `CategoriesView.vue` | — | Componente/listagem de categorias (usado no catálogo) |
| `ProductsView.vue` | — | Listagem de produtos por categoria |
| `ProductDetailView.vue` | — | Detalhe do produto, quantidade, add ao carrinho |
| `CartView.vue` | `/totem/carrinho` | Revisão do carrinho antes do pagamento |
| `PaymentView.vue` | `/totem/pagamento` | Seleção do método de pagamento |
| `ProcessingView.vue` | `/totem/processando` | Aguardando transação SiTef (bloqueia interação) |
| `SuccessView.vue` | `/totem/concluido` | Pedido concluído, cupom/impressão |
| `TimeoutView.vue` | `/totem/timeout` | Sessão encerrada por inatividade |

## Fluxo

Home → Catálogo → Carrinho → Pagamento → Processando → Concluído  
(Timeout pode interromper em qualquer etapa)

## Stores usadas

`catalog`, `cart`, `payment`, `session`
