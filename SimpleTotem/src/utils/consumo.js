// Escolha feita antes do pagamento (consumo no local / viagem). A Ticketera ainda não tem campo
// próprio no pedido, então a informação segue no `observacao` de cada item — é o que a cozinha
// recebe junto com o ticket. Quando houver campo dedicado, troque aqui e só aqui.
const ROTULOS = {
  local: 'CONSUMO NO LOCAL',
  viagem: 'PARA VIAGEM',
}

export function rotuloConsumo(modo) {
  return ROTULOS[modo] || ''
}

/** Observação do item para a Ticketera: "[PARA VIAGEM] sem cebola"; null se não há nada a enviar. */
export function observacaoComConsumo(notes, modo) {
  const rotulo = rotuloConsumo(modo)
  const texto = String(notes || '').trim()
  if (!rotulo) return texto || null
  return texto ? `[${rotulo}] ${texto}` : `[${rotulo}]`
}
