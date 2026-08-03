<template>
  <div class="cancelamento-panel">
    <div class="busca-form">
      <label class="busca-field">
        <span>Terminal</span>
        <input v-model.number="filtros.terminalId" type="number" min="1" placeholder="Ex: 3" />
      </label>
      <label class="busca-field">
        <span>Código da senha</span>
        <input v-model.trim="filtros.codigoSenha" type="text" placeholder="Ex: A123" />
      </label>
      <label class="busca-field">
        <span>Data da operação</span>
        <input v-model="filtros.dataOperacao" type="date" />
      </label>
      <button class="btn-primary" type="button" @click="buscar" :disabled="buscando">
        {{ buscando ? 'Buscando...' : 'Buscar' }}
      </button>
    </div>
    <p class="busca-hint">Preencha ao menos um campo para localizar o pedido.</p>

    <p v-if="erroBusca" class="feedback feedback--error">{{ erroBusca }}</p>

    <div v-if="buscando" class="loading-state">
      <span class="material-icons spinner-anim">progress_activity</span>
      Buscando pedidos...
    </div>

    <p v-else-if="pesquisou && pedidos.length === 0" class="placeholder-hint">
      Nenhum pedido encontrado para esses filtros.
    </p>

    <div v-else class="pedidos-list">
      <div v-for="pedido in pedidos" :key="pedido.id" class="pedido-card">
        <div class="pedido-header">
          <div>
            <span class="pedido-senha">Senha {{ pedido.codigo_senha }}</span>
            <span class="pedido-origem">{{ pedido.origem }} · terminal {{ pedido.terminal_id }}</span>
          </div>
          <span class="badge" :class="statusBadgeClass(pedido.status_pagamento)">
            {{ pedido.status_pagamento }}
          </span>
        </div>

        <div class="pedido-info">
          <p><strong>Data:</strong> {{ pedido.data_operacao }}</p>
          <p><strong>Documento fiscal:</strong> {{ pedido.documento ?? 'Não emitido' }}</p>
          <p><strong>Total:</strong> {{ formatMoeda(pedido.total) }}</p>
          <p><strong>Status do pedido:</strong> {{ pedido.status }}</p>
        </div>

        <div v-if="pedido.pagamento" class="pagamento-info">
          <h4>Pagamento</h4>
          <p><strong>Forma:</strong> {{ pedido.pagamento.forma_pagamento }} <span v-if="pedido.pagamento.bandeira">({{ pedido.pagamento.bandeira }})</span></p>
          <p><strong>Valor:</strong> {{ formatMoeda(pedido.pagamento.valor) }}</p>
          <p><strong>NSU:</strong> {{ pedido.pagamento.nsu ?? '—' }}</p>
          <p><strong>Autorização:</strong> {{ pedido.pagamento.codigo_autorizacao ?? '—' }}</p>
          <p v-if="pedido.pagamento.pago_em"><strong>Pago em:</strong> {{ pedido.pagamento.pago_em }}</p>
        </div>

        <button
          class="btn-toggle-itens"
          type="button"
          @click="pedido._itensAbertos = !pedido._itensAbertos"
        >
          {{ pedido._itensAbertos ? 'Ocultar itens' : `Ver itens (${pedido.itens?.length || 0})` }}
        </button>
        <ul v-if="pedido._itensAbertos" class="itens-list">
          <li v-for="(item, idx) in pedido.itens" :key="idx">
            {{ item.quantidade }}x {{ item.nome_produto }} — {{ formatMoeda(item.valor_total) }}
          </li>
        </ul>

        <p v-if="pedido.status_pagamento !== 'aprovado'" class="feedback feedback--muted">
          Pagamento com status "{{ pedido.status_pagamento }}" — não é possível estornar.
        </p>

        <template v-else>
          <button
            v-if="estornandoId !== pedido.id"
            class="btn-secondary btn-estornar"
            type="button"
            @click="abrirEstorno(pedido)"
          >
            Estornar
          </button>

          <div v-else class="estorno-form">
            <p class="estorno-warning">
              Ao confirmar, o cancelamento é enviado direto para a Fiserv (função SiTef 200, pelo NSU
              desta venda) — não emite nada à SEFAZ. Só marca como estornado aqui se a Fiserv confirmar.
            </p>
            <label class="busca-field">
              <span>Motivo do estorno</span>
              <textarea v-model="motivo" maxlength="500" rows="3" placeholder="Ex: cliente desistiu da compra após pagamento"></textarea>
            </label>
            <label class="busca-field">
              <span>Senha do supervisor para autorizar o cancelamento</span>
              <input
                v-model="senhaSupervisor"
                type="password"
                autocomplete="off"
                placeholder="Senha do supervisor"
              />
            </label>
            <p v-if="erroEstorno" class="feedback feedback--error">{{ erroEstorno }}</p>
            <div class="estorno-actions">
              <button class="btn-secondary" type="button" @click="cancelarEstorno" :disabled="confirmando">
                Cancelar
              </button>
              <button
                class="btn-primary"
                type="button"
                @click="confirmarEstorno(pedido)"
                :disabled="confirmando || !motivo.trim() || !senhaSupervisor.trim()"
              >
                {{ confirmando ? 'Cancelando na Fiserv...' : 'Confirmar estorno' }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'
import { sfListarPedidos, sfEstornarPedido } from '@/services/api'

const simplesfique = useSimpleSfiqueStore()

const filtros = ref({ terminalId: null, codigoSenha: '', dataOperacao: '' })
const pedidos = ref([])
const buscando = ref(false)
const pesquisou = ref(false)
const erroBusca = ref('')

const estornandoId = ref(null)
const motivo = ref('')
const senhaSupervisor = ref('')
const confirmando = ref(false)
const erroEstorno = ref('')

function formatMoeda(valor) {
  const num = Number(valor ?? 0)
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function statusBadgeClass(statusPagamento) {
  if (statusPagamento === 'aprovado') return 'badge--connected'
  if (statusPagamento === 'estornado') return 'badge--unknown'
  return 'badge--disconnected'
}

async function buscar() {
  const { terminalId, codigoSenha, dataOperacao } = filtros.value
  if (!terminalId && !codigoSenha && !dataOperacao) {
    erroBusca.value = 'Preencha ao menos um campo (terminal, código da senha ou data).'
    return
  }

  buscando.value = true
  erroBusca.value = ''
  pesquisou.value = true
  try {
    const resultado = await sfListarPedidos(
      { terminalId, codigoSenha, dataOperacao },
      simplesfique.jwtToken,
    )
    pedidos.value = (resultado?.pedidos || []).map(p => ({ ...p, _itensAbertos: false }))
  } catch (err) {
    erroBusca.value = err.message || 'Erro ao buscar pedidos'
    pedidos.value = []
  } finally {
    buscando.value = false
  }
}

function abrirEstorno(pedido) {
  estornandoId.value = pedido.id
  motivo.value = ''
  senhaSupervisor.value = ''
  erroEstorno.value = ''
}

function cancelarEstorno() {
  estornandoId.value = null
  motivo.value = ''
  senhaSupervisor.value = ''
  erroEstorno.value = ''
}

async function confirmarEstorno(pedido) {
  if (!motivo.value.trim() || !senhaSupervisor.value.trim()) return
  confirmando.value = true
  erroEstorno.value = ''
  try {
    const resultado = await sfEstornarPedido(pedido.id, motivo.value.trim(), senhaSupervisor.value.trim())
    const atualizado = resultado?.pedido
    if (atualizado) {
      const idx = pedidos.value.findIndex(p => p.id === pedido.id)
      if (idx !== -1) {
        pedidos.value[idx] = { ...pedidos.value[idx], ...atualizado }
      }
    }
    estornandoId.value = null
    motivo.value = ''
    senhaSupervisor.value = ''
  } catch (err) {
    erroEstorno.value = err.message || 'Erro ao estornar pedido'
  } finally {
    confirmando.value = false
    senhaSupervisor.value = ''
  }
}
</script>

<style scoped>
.cancelamento-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.placeholder-hint {
  color: #64748b;
  line-height: 1.5;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-2xl);
  text-align: center;
  color: #64748b;
  border-radius: var(--radius-md);
  background: rgba(245, 124, 0, 0.04);
}

.spinner-anim {
  font-size: 3rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.material-icons {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  font-feature-settings: 'liga';
  font-size: inherit;
  font-weight: inherit;
}

.badge {
  display: inline-block;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.badge--connected {
  background: rgba(76, 175, 80, 0.12);
  color: #4caf50;
}

.badge--disconnected {
  background: rgba(244, 67, 54, 0.12);
  color: #f44336;
}

.badge--unknown {
  background: rgba(158, 158, 158, 0.12);
  color: #9e9e9e;
}

.btn-primary {
  padding: var(--space-md) var(--space-xl);
  background: linear-gradient(135deg, #F57C00, #E27602);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: var(--font-size-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.25);
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: default;
}

.btn-secondary {
  padding: var(--space-md) var(--space-lg);
  background: rgba(245, 124, 0, 0.1);
  color: var(--color-primary);
  border: 2px solid rgba(245, 124, 0, 0.2);
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.15);
  border-color: rgba(245, 124, 0, 0.35);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: default;
}

.busca-form {
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
  align-items: flex-end;
}

.busca-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-weight: 600;
}

.busca-field input,
.busca-field textarea {
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
}

.busca-hint {
  margin: 0;
  font-size: var(--font-size-sm);
  color: #64748b;
}

.feedback {
  margin: 0;
  font-weight: 600;
}

.feedback--error {
  color: #c62828;
}

.feedback--muted {
  color: #64748b;
  font-weight: 500;
  font-size: var(--font-size-sm);
}

.pedidos-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.pedido-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-lg);
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.1);
  border-radius: var(--radius-md);
}

.pedido-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}

.pedido-senha {
  font-weight: 700;
  color: #0f172a;
  margin-right: var(--space-sm);
}

.pedido-origem {
  font-size: var(--font-size-sm);
  color: #64748b;
}

.pedido-info,
.pagamento-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.pedido-info p,
.pagamento-info p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: #0f172a;
}

.pagamento-info {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding-top: var(--space-sm);
}

.pagamento-info h4 {
  margin: 0 0 0.25rem;
  font-size: var(--font-size-sm);
  color: #64748b;
}

.btn-toggle-itens {
  align-self: flex-start;
  background: none;
  border: none;
  color: var(--color-primary);
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  font-size: var(--font-size-sm);
}

.itens-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: var(--font-size-sm);
  color: #0f172a;
}

.btn-estornar {
  align-self: flex-start;
}

.estorno-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding-top: var(--space-sm);
}

.estorno-warning {
  margin: 0;
  font-size: var(--font-size-sm);
  color: #c62828;
  font-weight: 600;
}

.estorno-actions {
  display: flex;
  gap: var(--space-sm);
}
</style>
