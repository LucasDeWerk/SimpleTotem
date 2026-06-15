<template>
  <div class="sync-routine">
    <div v-if="empresaLocal" class="empresa-vinculada">
      <p><strong>Empresa:</strong> {{ empresaLocal.nome_fantasia || empresaLocal.razao_social }}</p>
      <p><strong>id_saas:</strong> {{ empresaLocal.id_saas }} · <strong>id_empresa:</strong> {{ empresaLocal.id_empresa }}</p>
      <p v-if="sessao?.email"><strong>SimpleSfique:</strong> {{ sessao.email }}</p>
      <p v-if="sessao?.os_usuario"><strong>Usuário OS:</strong> {{ sessao.os_usuario }}</p>
    </div>

    <div class="sync-actions">
      <button
        class="btn-primary btn-large"
        :disabled="syncingAll"
        @click="sincronizarTudo"
      >
        <span class="material-icons">sync</span>
        {{ syncingAll ? 'Sincronizando tudo...' : 'Sincronizar tudo (fila)' }}
      </button>
    </div>

    <p v-if="globalError" class="sync-error">{{ globalError }}</p>

    <div class="etapas-list">
      <div
        v-for="etapa in etapas"
        :key="etapa.id"
        class="etapa-item"
        :class="{ running: runningId === etapa.id, done: etapa.ultimo_records > 0 }"
      >
        <div class="etapa-info">
          <span class="etapa-label">{{ etapa.label }}</span>
          <span class="etapa-meta">
            {{ etapa.ultimo_records || 0 }} registro(s)
            <template v-if="etapa.dh_sync"> · {{ formatDate(etapa.dh_sync) }}</template>
          </span>
        </div>
        <button
          class="btn-etapa"
          :disabled="syncingAll || runningId === etapa.id"
          @click="sincronizarEtapa(etapa.id)"
        >
          {{ runningId === etapa.id ? '...' : 'Sync' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import * as api from '@/services/api'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'
import { storeToRefs } from 'pinia'

const props = defineProps({
  empresaLocal: { type: Object, default: null }
})

const emit = defineEmits(['synced'])

const simplesfique = useSimpleSfiqueStore()
const { sessao } = storeToRefs(simplesfique)

const etapas = ref([])
const runningId = ref(null)
const syncingAll = ref(false)
const globalError = ref('')

function formatDate(value) {
  try {
    return new Date(value.replace(' ', 'T')).toLocaleString('pt-BR')
  } catch {
    return value
  }
}

async function carregarEtapas() {
  const data = await api.listarEtapasSync()
  etapas.value = data.etapas || []
}

async function sincronizarEtapa(etapaId) {
  runningId.value = etapaId
  globalError.value = ''
  try {
    await api.sincronizarEtapa(etapaId)
    await carregarEtapas()
    emit('synced')
  } catch (err) {
    globalError.value = err.message
  } finally {
    runningId.value = null
  }
}

async function sincronizarTudo() {
  syncingAll.value = true
  globalError.value = ''
  try {
    await api.sincronizarCompleto()
    await carregarEtapas()
    emit('synced')
  } catch (err) {
    globalError.value = err.message
  } finally {
    syncingAll.value = false
  }
}

onMounted(carregarEtapas)
</script>

<style scoped>
.sync-routine {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.empresa-vinculada {
  background: rgba(76, 175, 80, 0.08);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.empresa-vinculada p {
  margin: 0 0 var(--space-sm);
}

.sync-actions {
  display: flex;
  gap: var(--space-md);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: var(--space-md) var(--space-xl);
  background: linear-gradient(135deg, #f57c00, #e27602);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 700;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.sync-error {
  color: #f44336;
  background: rgba(244, 67, 54, 0.1);
  padding: var(--space-md);
  border-radius: var(--radius-md);
}

.etapas-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.etapa-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-md);
  background: white;
}

.etapa-item.running {
  border-color: #f57c00;
  background: rgba(245, 124, 0, 0.05);
}

.etapa-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.etapa-label {
  font-weight: 700;
  color: #0f172a;
}

.etapa-meta {
  font-size: var(--font-size-sm);
  color: #64748b;
}

.btn-etapa {
  min-width: 72px;
  min-height: 40px;
  border: 2px solid rgba(245, 124, 0, 0.3);
  border-radius: var(--radius-md);
  background: white;
  color: #f57c00;
  font-weight: 700;
  cursor: pointer;
}

.btn-etapa:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
