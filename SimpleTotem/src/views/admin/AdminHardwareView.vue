<template>
  <div class="admin-panel">
    <!-- Top Bar -->
    <header class="topbar">
      <div class="topbar-left">
        <h1 class="topbar-title">Configuração de Hardware</h1>
      </div>
      <div class="topbar-right">
        <button class="topbar-btn" @click="$router.push({ name: 'admin-panel' })">
          ← Voltar ao Painel
        </button>
      </div>
    </header>

    <main class="panel-content">

      <section
        v-for="secao in secoes"
        :key="secao.tipo"
        class="hw-section"
      >
        <h3 class="hw-section-title">{{ secao.label }}</h3>

        <!-- Config ativa -->
        <div class="hw-config-card" :class="{ 'hw-config-card--active': configAtiva[secao.tipo] }">
          <div v-if="configAtiva[secao.tipo]" class="hw-config-info">
            <p class="hw-config-nome">{{ configAtiva[secao.tipo].nome }}</p>
            <p class="hw-config-desc">{{ configAtiva[secao.tipo].descricao }}</p>
            <p class="hw-config-vid">{{ configAtiva[secao.tipo].vendor_id }}:{{ configAtiva[secao.tipo].product_id }}</p>
          </div>
          <div v-else class="hw-config-empty">
            <p>Nenhum dispositivo configurado</p>
          </div>
        </div>

        <!-- Ações -->
        <div class="hw-actions">
          <button
            class="hw-btn hw-btn-primary"
            @click="buscarDispositivos"
            :disabled="carregando"
          >
            {{ carregando ? 'Buscando...' : 'Buscar Dispositivos USB' }}
          </button>

          <button
            v-if="configAtiva[secao.tipo]"
            class="hw-btn hw-btn--danger"
            @click="removerConfig(secao.tipo)"
          >
            Remover Configuração
          </button>

          <button
            v-if="secao.tem_teste && configAtiva[secao.tipo]"
            class="hw-btn hw-btn-secondary"
            @click="testarImpressao"
            :disabled="testandoImpressao"
          >
            {{ testandoImpressao ? 'Testando...' : 'Testar Impressão' }}
          </button>
        </div>

        <!-- Resultado de teste -->
        <p
          v-if="secao.tem_teste && resultadoTeste"
          class="hw-resultado"
          :class="resultadoTeste.startsWith('Impressão') ? 'hw-resultado--ok' : 'hw-resultado--erro'"
        >
          {{ resultadoTeste }}
        </p>

        <!-- Lista USB -->
        <div v-if="dispositivosUSB.length > 0" class="hw-usb-list">
          <div
            v-for="(dev, idx) in dispositivosUSB"
            :key="idx"
            class="hw-usb-card"
            :class="{ 'hw-usb-card--selected': isConfigured(secao.tipo, dev) }"
          >
            <div class="hw-usb-info">
              <p class="hw-usb-produto">{{ dev.produto }}</p>
              <p class="hw-usb-fabricante">{{ dev.fabricante }}</p>
              <p class="hw-usb-vid">{{ dev.vendorId }}:{{ dev.productId }}</p>
            </div>
            <button
              class="hw-btn hw-btn--sm"
              @click="selecionarDispositivo(secao.tipo, dev)"
              :disabled="isConfigured(secao.tipo, dev)"
            >
              {{ isConfigured(secao.tipo, dev) ? 'Configurado' : 'Selecionar' }}
            </button>
          </div>
        </div>
      </section>

    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  listarDispositivosUSB as listarUSBApi,
  salvarConfigHardware,
  obterConfigHardware,
  removerConfigHardware
} from '@/services/api'

const secoes = [
  { tipo: 'impressora', label: 'Impressora Térmica', tem_teste: true },
  { tipo: 'leitor_barcode', label: 'Leitor de Código de Barras', tem_teste: false },
  { tipo: 'terminal_pagamento', label: 'Terminal de Pagamento', tem_teste: false }
]

const dispositivosUSB = ref([])
const carregando = ref(false)
const testandoImpressao = ref(false)
const resultadoTeste = ref(null)
const configAtiva = ref({
  impressora: null,
  leitor_barcode: null,
  terminal_pagamento: null
})

function isConfigured(tipo, dev) {
  const cfg = configAtiva.value[tipo]
  if (!cfg) return false
  return cfg.vendor_id === dev.vendorId && cfg.product_id === dev.productId
}

async function carregarConfigs() {
  const [impressora, leitor, terminal] = await Promise.all([
    obterConfigHardware('impressora'),
    obterConfigHardware('leitor_barcode'),
    obterConfigHardware('terminal_pagamento')
  ])
  configAtiva.value.impressora = impressora
  configAtiva.value.leitor_barcode = leitor
  configAtiva.value.terminal_pagamento = terminal
}

async function buscarDispositivos() {
  carregando.value = true
  dispositivosUSB.value = []
  try {
    dispositivosUSB.value = await listarUSBApi()
  } catch (e) {
    console.error('[Hardware] Erro ao listar USB:', e)
  } finally {
    carregando.value = false
  }
}

async function selecionarDispositivo(tipo, device) {
  await salvarConfigHardware({
    tipo_dispositivo: tipo,
    nome: device.produto,
    vendor_id: device.vendorId,
    product_id: device.productId,
    descricao: device.fabricante + ' ' + device.produto
  })
  configAtiva.value[tipo] = await obterConfigHardware(tipo)
}

async function removerConfig(tipo) {
  await removerConfigHardware(tipo)
  configAtiva.value[tipo] = null
}

async function testarImpressao() {
  testandoImpressao.value = true
  resultadoTeste.value = null
  try {
    const result = await window.electronAPI.printer.testPrint()
    resultadoTeste.value = result.success
      ? 'Impressão realizada com sucesso!'
      : ('Erro: ' + result.message)
  } catch (e) {
    resultadoTeste.value = 'Erro: ' + e.message
  } finally {
    testandoImpressao.value = false
  }
}

onMounted(() => {
  carregarConfigs()
})
</script>

<style scoped>
.admin-panel {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(
    135deg,
    #fef9f5 0%,
    #fef5f0 50%,
    #fdeee7 100%
  );
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-xl);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(245, 124, 0, 0.08);
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.1);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.topbar-icon {
  font-size: 1.8rem;
}

.topbar-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.topbar-btn {
  background: rgba(245, 124, 0, 0.08);
  color: var(--color-primary);
  border: 1px solid rgba(245, 124, 0, 0.15);
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-md);
  font-weight: 700;
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.5px;
  font-size: var(--font-size-md);
}

.topbar-btn:hover {
  background: rgba(245, 124, 0, 0.12);
  border-color: rgba(245, 124, 0, 0.3);
  transform: translateX(-2px);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
}

/* Section */
.hw-section {
  margin-bottom: var(--space-xl);
}

.hw-section-title {
  font-size: var(--font-size-xl);
  font-weight: 900;
  color: #0f172a;
  margin: 0 0 var(--space-lg);
  letter-spacing: -0.02em;
  padding-bottom: var(--space-lg);
  border-bottom: 2px solid rgba(245, 124, 0, 0.08);
}

/* Config Card */
.hw-config-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.08);
  padding: var(--space-lg);
  border: 1px solid rgba(245, 124, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  margin-bottom: var(--space-md);
}

.hw-config-card:hover {
  transform: translateY(-2px);
  border-color: rgba(245, 124, 0, 0.15);
  box-shadow: 0 12px 32px rgba(245, 124, 0, 0.15);
}

.hw-config-card--active {
  border: 2px solid #F57C00;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.2);
}

.hw-config-nome {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: var(--color-primary);
  margin: 0 0 var(--space-sm);
}

.hw-config-desc {
  font-size: var(--font-size-sm);
  color: #0f172a;
  margin: 0 0 4px;
  font-weight: 500;
}

.hw-config-vid {
  font-size: var(--font-size-xs);
  color: #64748b;
  font-family: monospace;
  margin: 0;
  opacity: 0.8;
}

.hw-config-empty p {
  color: #64748b;
  font-size: var(--font-size-sm);
  margin: 0;
  font-weight: 500;
}

/* Actions */
.hw-actions {
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
  margin-bottom: var(--space-md);
}

/* Buttons */
.hw-btn {
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: var(--font-size-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
  letter-spacing: 0.5px;
}

.hw-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.hw-btn-primary {
  background: linear-gradient(135deg, #F57C00, #E27602);
  color: white;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.25);
}

.hw-btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.3);
}

.hw-btn-secondary {
  background: rgba(245, 124, 0, 0.08);
  color: var(--color-primary);
  border: 1px solid rgba(245, 124, 0, 0.15);
}

.hw-btn-secondary:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.12);
  border-color: rgba(245, 124, 0, 0.3);
}

.hw-btn-danger {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  border: 1px solid rgba(244, 67, 54, 0.15);
}

.hw-btn-danger:hover:not(:disabled) {
  background: rgba(244, 67, 54, 0.15);
  border-color: rgba(244, 67, 54, 0.3);
}

/* Device List */
.hw-device-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.hw-device-item {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  border: 1px solid rgba(245, 124, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  transition: all 0.3s ease;
  cursor: pointer;
}

.hw-device-item:hover {
  transform: translateX(4px);
  border-color: rgba(245, 124, 0, 0.15);
  background: rgba(245, 124, 0, 0.04);
}

.hw-device-info {
  flex: 1;
}

.hw-device-name {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px;
}

.hw-device-desc {
  font-size: var(--font-size-sm);
  color: #64748b;
  margin: 0;
}

/* Loading */
.hw-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  color: #64748b;
}

.hw-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(245, 124, 0, 0.15);
  border-top-color: #F57C00;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty State */
.hw-empty {
  text-align: center;
  padding: var(--space-2xl);
  color: #64748b;
}

.hw-empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-lg);
  opacity: 0.5;
}

/* ===== Responsividade ===== */
@media (max-width: 768px) {
  .topbar {
    flex-direction: column;
    gap: var(--space-md);
    align-items: flex-start;
  }

  .topbar-title {
    font-size: var(--font-size-xl);
  }

  .panel-content {
    padding: var(--space-lg);
    gap: var(--space-lg);
  }

  .hw-device-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .hw-actions {
    flex-direction: column;
  }

  .hw-btn {
    width: 100%;
  }
}
</style>
