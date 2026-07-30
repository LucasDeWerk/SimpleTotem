# Scaffold — components/shared/

Componentes **reutilizáveis** do totem. Import via `@/components/shared/`.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `ScreenContainer.vue` | Wrapper de tela — padding, layout base |
| `TotemHeader.vue` | Cabeçalho com título e botão voltar |
| `PrimaryActionButton.vue` | Botão de ação principal (CTA) |
| `FloatingCartButton.vue` | Botão flutuante do carrinho com badge |
| `CategoryCard.vue` | Card de categoria/grupo no catálogo |
| `ProductCard.vue` | Card de produto na listagem |
| `CartItemRow.vue` | Linha de item no carrinho |
| `QuantityStepper.vue` | Stepper +/- de quantidade |
| `PaymentMethodCard.vue` | Card de seleção de método de pagamento |
| `TimeoutOverlay.vue` | Overlay de aviso antes do timeout de sessão |

## Convenção

Componentes presentacionais — lógica de negócio fica em stores/composables.
