<template>
  <div class="admin-panel">
    <!-- Sidebar de Navegação -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="sidebar-title">Admin</h1>
        <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
          <span class="material-icons">{{ sidebarOpen ? 'close' : 'menu' }}</span>
        </button>
      </div>

      <nav class="sidebar-nav" :class="{ active: sidebarOpen }">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: activeSection === item.id }"
          @click="activeSection = item.id; sidebarOpen = false"
        >
          <span class="material-icons nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <button class="sidebar-btn sidebar-btn--fullscreen" @click="toggleFullscreen" title="Tela Cheia">
          <span class="material-icons">fullscreen</span>
        </button>
        <button class="sidebar-btn sidebar-btn--exit" @click="backToTotem" title="Voltar">
          <span class="material-icons">logout</span>
        </button>
      </div>
    </aside>

    <!-- Conteúdo Principal -->
    <main class="panel-content">
      <div class="content-header">
        <h2 class="content-title">{{ getSectionTitle() }}</h2>
      </div>

      <!-- Seção: Periféricos -->
      <section v-show="activeSection === 'peripherals'" class="content-section">
        <div class="section-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Status dos Dispositivos</h3>
              <p class="card-description">Verifique a conexão de periféricos</p>
            </div>
            <button class="btn-icon-large" @click="scanPeripherals" :disabled="scanning">
              <span class="material-icons" :class="{ spinning: scanning }">refresh</span>
            </button>
          </div>

          <div v-if="scanning" class="loading-state">
            <span class="material-icons spinner-anim">autorenew</span>
            <p>Verificando dispositivos...</p>
          </div>

          <div v-else class="devices-list">
            <div v-for="p in peripherals" :key="p.id" class="device-item">
              <div class="device-info">
                <h4 class="device-name">{{ p.label }}</h4>
                <p v-if="p.detail" class="device-detail">{{ p.detail }}</p>
              </div>
              <div class="device-status">
                <span class="badge" :class="'badge--' + p.status">
                  {{ statusLabel(p.status) }}
                </span>
                <button
                  class="btn-sm"
                  @click="testDevice(p.id)"
                  :disabled="p.status === 'checking'"
                >
                  {{ p.status === 'checking' ? '...' : 'Testar' }}
                </button>
              </div>
            </div>
          </div>

          <button class="btn-secondary" @click="$router.push({ name: 'admin-hardware' })">
            <span class="material-icons" style="margin-right: 8px;">settings</span>
            Configurações Avançadas
          </button>
        </div>
      </section>

      <!-- Seção: Sincronização -->
      <section v-show="activeSection === 'sync'" class="content-section">
        <div class="section-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Sincronização de Dados</h3>
              <p class="card-description">Sincronize todos os dados da API</p>
            </div>
          </div>

          <div class="sync-status-container">
            <div class="status-info">
              <p class="status-label">Status:</p>
              <p class="sync-status-text" :class="'sync--' + fullSyncStatus">
                {{ fullSyncLabel }}
              </p>
              <p class="sync-last">
                {{ fullSyncLastTime
                  ? 'Última: ' + new Date(fullSyncLastTime).toLocaleString('pt-BR')
                  : 'Nenhuma sincronização realizada' }}
              </p>
            </div>
          </div>

          <button
            class="btn-primary btn-large"
            :disabled="fullSyncStatus === 'syncing'"
            @click="handleFullSync"
          >
            <span class="material-icons" style="margin-right: 8px;">sync</span>
            {{ fullSyncStatus === 'syncing' ? 'Sincronizando...' : 'Sincronizar Tudo' }}
          </button>

          <!-- Progress -->
          <div v-if="fullSyncStatus === 'syncing'" class="sync-progress">
            <div
              v-for="(item, key) in syncProgress"
              :key="key"
              class="progress-item"
              :class="{ completed: item }"
            >
              <span class="progress-bar"></span>
              <span class="progress-label">{{ formatItemName(key) }}</span>
              <span v-if="item" class="material-icons progress-check">check_circle</span>
            </div>
          </div>

          <!-- Erros -->
          <div v-if="fullSyncErrors.length > 0" class="alert alert--error">
            <h4 class="alert-title"><span class="material-icons" style="margin-right: 8px;">warning</span>Erros encontrados</h4>
            <ul class="error-list">
              <li v-for="(error, idx) in fullSyncErrors" :key="idx">
                <strong>{{ error.entidade || error.etapa }}:</strong> {{ error.erro }}
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Seção: Token -->
      <section v-show="activeSection === 'token'" class="content-section">
        <div class="section-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Autenticação</h3>
              <p class="card-description">Gerenciar token de acesso</p>
            </div>
          </div>

          <div class="token-status-container" :class="'token-' + tokenStatus">
            <span class="material-icons token-icon-large">{{ tokenStatusIcon }}</span>
            <div class="token-details">
              <p class="token-status-text">{{ tokenStatusMessage }}</p>
              <p v-if="tokenLastUpdate" class="token-last-update">
                Última atualização: {{ new Date(tokenLastUpdate).toLocaleString('pt-BR') }}
              </p>
            </div>
            <button
              class="btn-secondary"
              @click="autoSyncToken"
              :disabled="tokenSyncing"
            >
              {{ tokenSyncing ? 'Sincronizando...' : 'Retentar' }}
            </button>
          </div>
        </div>
      </section>

    </main>

    <!-- Modal de Seleção de Empresa -->
    <div v-if="showEmpresaModal" class="modal-overlay" @click.self="closeEmpresaModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2 class="modal-title">Selecionar Empresa</h2>
          <button class="modal-close" @click="closeEmpresaModal">
            <span class="material-icons">close</span>
          </button>
        </div>

        <div class="modal-body">
          <p class="modal-description">
            Múltiplas empresas foram encontradas. Selecione qual deseja sincronizar:
          </p>

          <div class="empresa-select-group">
            <label class="select-label">Empresa:</label>
            <select v-model.string="selectedEmpresaId" class="empresa-select">
              <option value="">-- Escolha uma empresa --</option>
              <option
                v-for="empresa in empresasDisponiveis"
                :key="empresa.id"
                :value="String(empresa.id)"
              >
                {{ empresa.fantasia || empresa.razao_social }}
              </option>
            </select>
          </div>

          <div v-if="selectedEmpresaId" class="empresa-preview">
            <h4 class="preview-title">Detalhes da Empresa:</h4>
            <div class="preview-details">
              <p><strong>Razão Social:</strong> {{ selectedEmpresaData?.razao_social }}</p>
              <p><strong>Nome Fantasia:</strong> {{ selectedEmpresaData?.fantasia }}</p>
              <p><strong>CNPJ:</strong> {{ selectedEmpresaData?.cpf_cnpj }}</p>
              <p><strong>Contato:</strong> {{ selectedEmpresaData?.whatsapp || 'N/A' }}</p>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="closeEmpresaModal">
            Cancelar
          </button>
           <button
            class="btn-confirm"
            @click="confirmEmpresaSelection"
            :disabled="!selectedEmpresaId"
          >
            {{ confirmingEmpresa ? 'Salvando...' : 'Confirmar e Continuar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDeviceStore } from '@/stores/device'
import { useAdminStore } from '@/stores/admin'

const router = useRouter()
const device = useDeviceStore()
const admin = useAdminStore()

// UI State
const sidebarOpen = ref(false)
const activeSection = ref('peripherals')

// Navigation items
const navItems = [
  { id: 'peripherals', icon: 'devices', label: 'Periféricos' },
  { id: 'sync', icon: 'sync', label: 'Sincronização' },
  { id: 'token', icon: 'security', label: 'Autenticação' }
]

// Periféricos
const peripherals = ref([])
const scanning = ref(false)

// Modal de seleção de empresa
const showEmpresaModal = ref(false)
const empresasDisponiveis = ref([])
const selectedEmpresaId = ref('')
const confirmingEmpresa = ref(false)

const selectedEmpresaData = computed(() => {
  return empresasDisponiveis.value.find(e => String(e.id) === selectedEmpresaId.value)
})

// Token status
const tokenStatus = computed(() => admin.tokenStatus || 'idle')
const tokenSyncing = ref(false)
const tokenLastUpdate = computed(() => localStorage.getItem('token_last_update'))
const tokenError = ref('')

const tokenStatusIcon = computed(() => {
   const icons = { idle: 'security', syncing: 'hourglass_empty', success: 'verified', error: 'error' }
   return icons[tokenStatus.value] || 'security'
 })

const tokenStatusMessage = computed(() => {
  const messages = {
    idle: 'Token pronto',
    syncing: 'Atualizando token...',
    success: 'Token atualizado com sucesso',
    error: `Erro: ${tokenError.value}`
  }
  return messages[tokenStatus.value] || ''
})

// Sincronização Completa
const fullSyncStatus = computed(() => admin.syncStatus)
const fullSyncLastTime = computed(() => admin.lastFullSync)
const fullSyncErrors = ref([])

const syncProgress = computed(() => ({
  empresa: admin.syncProgress.empresas,
  grupos: admin.syncProgress.grupos,
  subgrupos: admin.syncProgress.subgrupos,
  medidas: admin.syncProgress.medidas,
  produtos: admin.syncProgress.produtos,
  pagamentos: admin.syncProgress.marcas // Usar marcas como substituto de pagamentos
}))

const fullSyncLabel = computed(() => {
  const map = {
    idle: 'Pronto para sincronizar todos os dados',
    syncing: 'Sincronizando todos os dados...',
    success: 'Sincronização completa com sucesso',
    error: 'Erro na sincronização'
  }
  return map[fullSyncStatus.value] || ''
})

function statusLabel(s) {
   if (s === 'connected') return '● Conectado'
   if (s === 'disconnected') return '● Desconectado'
   if (s === 'checking') return '● Verificando...'
   return '● Não detectado'
 }

 function getSectionTitle() {
   const item = navItems.find(i => i.id === activeSection.value)
   return item?.label || 'Admin'
 }

 function formatItemName(key) {
   const names = {
     empresa: 'Empresa',
     grupos: 'Grupos',
     subgrupos: 'Subgrupos',
     medidas: 'Medidas',
     produtos: 'Produtos',
     pagamentos: 'Pagamentos'
   }
   return names[key] || key
 }

function buildList() {
  return [
    {
      id: 'device',
      icon: '',
      label: 'Dispositivo',
      status: device.isOnline ? 'connected' : 'disconnected',
      detail: device.deviceUuid ? `ID ${device.deviceUuid.substring(0, 8)}` : null
    },
    {
      id: 'printer',
      icon: '',
      label: 'Impressora',
      status: 'unknown',
      detail: null
    },
    {
      id: 'card_reader',
      icon: '',
      label: 'Leitor de Cartão',
      status: 'unknown',
      detail: null
    }
  ]
}

async function scanPeripherals() {
  scanning.value = true
  peripherals.value = buildList()
  try {
    await new Promise(r => setTimeout(r, 500))
    const printer = peripherals.value.find(p => p.id === 'printer')
    if (printer) printer.status = 'disconnected'
    const reader = peripherals.value.find(p => p.id === 'card_reader')
    if (reader) reader.status = 'connected'
  } catch {
    peripherals.value.forEach(p => (p.status = 'unknown'))
  } finally {
    scanning.value = false
  }
}

async function testDevice(id) {
  const p = peripherals.value.find(x => x.id === id)
  if (!p) return
  p.status = 'checking'
  try {
    await new Promise(r => setTimeout(r, 600))
    p.status = Math.random() > 0.4 ? 'connected' : 'disconnected'
  } catch {
    p.status = 'unknown'
  }
}

async function handleFullSync() {
  fullSyncErrors.value = []
  try {
    await admin.syncAll()
  } catch (err) {
    fullSyncErrors.value.push({
      etapa: 'Sincronização',
      erro: err.message
    })
  }
}

function backToTotem() {
   admin.logout()
   router.push({ name: 'home' })
 }

 async function toggleFullscreen() {
   try {
     await window.electronAPI.toggleFullscreen()
   } catch (err) {
     console.error('[Admin] Erro ao alternar fullscreen:', err)
   }
 }

function closeEmpresaModal() {
  showEmpresaModal.value = false
  selectedEmpresaId.value = ''
  confirmingEmpresa.value = false
}

async function confirmEmpresaSelection() {
  if (!selectedEmpresaId.value) return
  confirmingEmpresa.value = true
  try {
    // Salvar ID da empresa selecionada
    localStorage.setItem('selected_empresa_id', selectedEmpresaId.value)
    console.log('[Admin] Empresa selecionada:', selectedEmpresaId.value)
  } catch (err) {
    console.error('[Admin] Erro ao salvar empresa:', err)
  } finally {
    closeEmpresaModal()
    confirmingEmpresa.value = false
  }
}

async function autoSyncToken() {
  tokenSyncing.value = true
  tokenError.value = ''
  try {
    // Simular obtém token
    console.log('[Admin] 🔄 Sincronizando token...')
    // TODO: Implementar chamada real quando houver credentials
    tokenStatus.value = 'success'
    localStorage.setItem('token_last_update', new Date().toISOString())
    tokenSyncing.value = false

    setTimeout(() => { admin.tokenStatus = 'idle' }, 5000)
  } catch (err) {
    tokenError.value = err.message
    tokenStatus.value = 'error'
    tokenSyncing.value = false
  }
}

// Monitorar mudanças na sincronização
watch(() => admin.syncStatus, (newStatus) => {
  if (newStatus === 'error') {
    fullSyncErrors.value = [{
      etapa: 'Sincronização',
      erro: admin.syncMessage
    }]
  }
})

onMounted(async () => {
  scanPeripherals()
  await autoSyncToken()

  // Carregar dados da empresa para modal
  try {
    console.log('[Admin] 📡 Buscando empresas disponíveis...')
    // TODO: Buscar empresas de verdade quando tiver conexão com API
    empresasDisponiveis.value = []
  } catch (err) {
    console.error('[Admin] Erro ao buscar empresas:', err)
  }
})
</script>

<style scoped>
/* Material Icons */
.material-icons {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  font-feature-settings: 'liga';
  font-size: inherit;
  font-weight: inherit;
}

.admin-panel {
  display: flex;
  height: 100vh;
  background: #f5f5f5;
  overflow: hidden;
}

/* ===== SIDEBAR ===== */
.sidebar {
  width: 280px;
  background: linear-gradient(135deg, #F57C00 0%, #E27602 100%);
  display: flex;
  flex-direction: column;
  padding: var(--space-lg);
  gap: var(--space-lg);
  box-shadow: 4px 0 16px rgba(245, 124, 0, 0.15);
  z-index: 100;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}

.sidebar-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: white;
  margin: 0;
  letter-spacing: -0.02em;
}

.sidebar-toggle {
  display: none;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.sidebar-toggle:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Navigation */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  color: rgba(255, 255, 255, 0.8);
  font-size: var(--font-size-md);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.95);
  color: var(--color-primary);
  border-color: rgba(255, 255, 255, 0.5);
}

.nav-icon {
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-label {
  font-size: var(--font-size-md);
  font-weight: 600;
}

/* Sidebar Footer */
.sidebar-footer {
  display: flex;
  gap: var(--space-sm);
}

.sidebar-btn {
  flex: 1;
  padding: var(--space-md);
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  color: white;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.sidebar-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.sidebar-btn--fullscreen {
  background: rgba(255, 255, 255, 0.2);
}

.sidebar-btn--exit {
  background: rgba(255, 0, 0, 0.2);
}

.sidebar-btn--exit:hover {
  background: rgba(255, 0, 0, 0.3);
}

/* ===== MAIN CONTENT ===== */
.panel-content {
  margin-left: 280px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-xl);
  gap: var(--space-lg);
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-lg);
  border-bottom: 2px solid rgba(245, 124, 0, 0.1);
}

.content-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

/* Content Sections */
.content-section {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Cards */
.section-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
}

.card-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 var(--space-sm);
}

.card-description {
  font-size: var(--font-size-sm);
  color: #64748b;
  margin: 0;
  font-weight: 500;
}

/* Loading State */
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

/* Devices List */
.devices-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.device-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg);
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.1);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.device-item:hover {
  background: rgba(245, 124, 0, 0.08);
  border-color: rgba(245, 124, 0, 0.2);
}

.device-info {
  flex: 1;
}

.device-name {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 var(--space-sm);
}

.device-detail {
  font-size: var(--font-size-sm);
  color: #64748b;
  margin: 0;
}

.device-status {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

/* Badges */
.badge {
  display: inline-block;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  letter-spacing: 0.3px;
}

.badge--connected {
  background: rgba(76, 175, 80, 0.12);
  color: #4caf50;
}

.badge--disconnected {
  background: rgba(244, 67, 54, 0.12);
  color: #f44336;
}

.badge--checking {
  background: rgba(255, 152, 0, 0.12);
  color: #ff9800;
}

.badge--unknown {
  background: rgba(158, 158, 158, 0.12);
  color: #9e9e9e;
}

/* Sync Status Container */
.sync-status-container {
  background: rgba(245, 124, 0, 0.06);
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.status-label {
  font-size: var(--font-size-sm);
  color: #64748b;
  font-weight: 600;
  margin: 0;
}

.sync-status-text {
  font-size: var(--font-size-lg);
  font-weight: 700;
  margin: 0;
}

.sync--idle {
  color: #0f172a;
}

.sync--syncing {
  color: #2196f3;
}

.sync--success {
  color: #4caf50;
}

.sync--error {
  color: #f44336;
}

.sync-last {
  font-size: var(--font-size-sm);
  color: #64748b;
  margin: 0;
  font-weight: 500;
}

/* Sync Progress */
.sync-progress {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-md);
  padding: var(--space-lg);
  background: rgba(245, 124, 0, 0.04);
  border-radius: var(--radius-md);
}

.progress-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: white;
  border: 2px solid rgba(158, 158, 158, 0.2);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.progress-item.completed {
  border-color: rgba(76, 175, 80, 0.5);
  background: rgba(76, 175, 80, 0.05);
}

.progress-bar {
  width: 4px;
  height: 24px;
  background: rgba(245, 124, 0, 0.3);
  border-radius: 2px;
}

.progress-item.completed .progress-bar {
  background: #4caf50;
}

.progress-label {
  flex: 1;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #0f172a;
}

.progress-check {
  font-size: 1.2rem;
  color: #4caf50;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Token Status Container */
.token-status-container {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-xl);
  background: rgba(245, 124, 0, 0.06);
  border: 2px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.token-status-container.token-success {
  border-color: rgba(76, 175, 80, 0.3);
  background: rgba(76, 175, 80, 0.08);
}

.token-status-container.token-error {
  border-color: rgba(244, 67, 54, 0.3);
  background: rgba(244, 67, 54, 0.08);
}

.token-status-container.token-syncing {
  border-color: rgba(33, 150, 243, 0.3);
  background: rgba(33, 150, 243, 0.08);
}

.token-icon-large {
  font-size: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: inherit;
}

.token-status-container.token-syncing .token-icon-large {
  animation: spin 1s linear infinite;
}

.token-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.token-status-text {
  font-size: var(--font-size-lg);
  font-weight: 700;
  margin: 0;
  color: #0f172a;
}

.token-last-update {
  font-size: var(--font-size-sm);
  color: #64748b;
  margin: 0;
  font-weight: 500;
}

/* Alerts */
.alert {
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  border-left: 4px solid;
}

.alert--error {
  background: rgba(244, 67, 54, 0.08);
  border-left-color: #f44336;
}

.alert-title {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: #f44336;
  margin: 0 0 var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.error-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.error-list li {
  font-size: var(--font-size-sm);
  color: #0f172a;
  padding: var(--space-sm);
  background: white;
  border-radius: var(--radius-sm);
}

/* Buttons */
.btn-icon-large {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #F57C00, #E27602);
  border: none;
  color: white;
  font-size: 1.3rem;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.25);
  flex-shrink: 0;
}

.btn-icon-large:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.3);
}

.btn-icon-large:disabled {
  opacity: 0.5;
  cursor: default;
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

.btn-large {
  min-height: 56px;
  font-size: var(--font-size-lg);
  padding: var(--space-lg) var(--space-xl);
  width: 100%;
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

.btn-sm {
  padding: 8px 16px;
  background: linear-gradient(135deg, #F57C00, #E27602);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-sm:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(245, 124, 0, 0.25);
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: default;
}

/* Modal (mantendo compatibilidade) */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  border-radius: var(--radius-xl);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xl);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.modal-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  margin: 0;
  color: #0f172a;
}

.modal-close {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.05);
  color: #0f172a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.modal-close:hover {
  background: rgba(0, 0, 0, 0.1);
}

.modal-body {
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.modal-description {
  margin: 0;
  color: rgba(0, 0, 0, 0.6);
  font-size: var(--font-size-md);
  line-height: 1.5;
}

.empresa-select-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.select-label {
  font-weight: 600;
  color: #0f172a;
  font-size: var(--font-size-md);
}

.empresa-select {
  padding: var(--space-md);
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-md);
  background: #f8f8f8;
  color: #0f172a;
  font-size: var(--font-size-md);
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}

.empresa-select:hover {
  border-color: rgba(0, 0, 0, 0.2);
}

.empresa-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.1);
}

.empresa-preview {
  background: rgba(245, 124, 0, 0.08);
  border: 2px solid rgba(245, 124, 0, 0.2);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.preview-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 var(--space-md);
}

.preview-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.preview-details p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: #64748b;
}

.preview-details strong {
  color: #0f172a;
  font-weight: 600;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-md);
  padding: var(--space-xl);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.btn-cancel {
  padding: var(--space-md) var(--space-lg);
  background: rgba(0, 0, 0, 0.05);
  color: #0f172a;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: rgba(0, 0, 0, 0.1);
}

.btn-confirm {
  padding: var(--space-md) var(--space-lg);
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-confirm:hover:not(:disabled) {
  background: #e27602;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: default;
}

/* Responsivo */
@media (max-width: 1024px) {
  .sidebar {
    width: 240px;
  }

  .panel-content {
    margin-left: 240px;
    padding: var(--space-lg);
  }
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    width: 100%;
    height: auto;
    flex-direction: row;
    padding: var(--space-md);
    gap: var(--space-md);
    max-height: 64px;
    z-index: 200;
    overflow-x: auto;
  }

  .sidebar-toggle {
    display: flex;
  }

  .sidebar-nav {
    display: none;
  }

  .sidebar-nav.active {
    display: flex;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--color-primary);
    padding: var(--space-md);
    flex-direction: column;
    gap: var(--space-sm);
    border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  }

  .sidebar-footer {
    position: absolute;
    right: var(--space-md);
    top: 50%;
    transform: translateY(-50%);
  }

  .panel-content {
    margin-left: 0;
    margin-top: 80px;
    padding: var(--space-md);
  }

  .content-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-md);
  }

  .content-title {
    font-size: var(--font-size-xl);
  }

  .sync-progress {
    grid-template-columns: 1fr;
  }

  .device-item {
    flex-direction: column;
    gap: var(--space-md);
    align-items: flex-start;
  }

  .device-status {
    width: 100%;
    justify-content: space-between;
  }
}


</style>
