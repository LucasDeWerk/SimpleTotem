import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCartStore = defineStore('cart', () => {
  const items = ref([])
  const itemCount = computed(() => {
    return items.value.reduce((total, item) => total + item.quantity, 0)
  })
  const subtotal = computed(() => {
    return items.value.reduce((total, item) => total + item.totalPrice, 0)
  })
  const discount = ref(0)
  const total = computed(() => {
    return Math.max(0, subtotal.value - discount.value)
  })
  const vendaCalculada = ref(null)
  const calculandoVenda = ref(false)
  const erroCalculo = ref(null)

  function addItem(product, quantity = 1, notes = '', modifiers = []) {
    const existingIndex = items.value.findIndex(
      item => item.productId === product.id && JSON.stringify(item.modifiers) === JSON.stringify(modifiers)
    )
    if (existingIndex >= 0) {
      items.value[existingIndex].quantity += quantity
      items.value[existingIndex].totalPrice = items.value[existingIndex].quantity * items.value[existingIndex].unitPrice
    } else {
      const modifiersPrice = modifiers.reduce((sum, m) => sum + Number(m.price || 0), 0)
      const unitPrice = Number(product.price || 0) + modifiersPrice
      items.value.push({
        productId: product.id,
        name: product.name,
        image: product.image || '',
        quantity,
        unitPrice,
        totalPrice: unitPrice * quantity,
        notes,
        modifiers,
        menu_id: product.menu_id ?? null,
        ambiente_preparo_id: product.ambiente_preparo_id ?? null,
        emite_ticket: product.emite_ticket ?? true,
      })
    }
    vendaCalculada.value = null
  }

  function removeItem(index) {
    items.value.splice(index, 1)
    vendaCalculada.value = null
  }

  function updateQuantity(index, quantity) {
    if (quantity <= 0) {
      removeItem(index)
      return
    }
    items.value[index].quantity = quantity
    items.value[index].totalPrice = items.value[index].unitPrice * quantity
    vendaCalculada.value = null
  }

  function clearCart() {
    items.value = []
    discount.value = 0
    vendaCalculada.value = null
    erroCalculo.value = null
  }

  /** Calcula totais localmente — preços vêm do catálogo SimplesFique */
  async function calcularVenda() {
    if (items.value.length === 0) return
    calculandoVenda.value = true
    erroCalculo.value = null
    try {
      const sub = items.value.reduce((sum, item) => sum + item.totalPrice, 0)
      vendaCalculada.value = {
        subtotal: sub,
        desconto: discount.value,
        total: Math.max(0, sub - discount.value),
      }
    } catch (err) {
      erroCalculo.value = err.message || 'Erro ao calcular venda'
    } finally {
      calculandoVenda.value = false
    }
  }

  return {
    items,
    itemCount,
    subtotal,
    discount,
    total,
    vendaCalculada,
    calculandoVenda,
    erroCalculo,
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    calcularVenda,
  }
})
