<template>
  <div class="totem-login-view">
    <div class="login-content animate-fade-in">

      <!-- Indicador de passo -->
      <div class="step-indicator">
        <span
          v-for="n in 3"
          :key="n"
          class="step-dot"
          :class="{ active: n === step, done: n < step }"
        ></span>
        <span class="step-label">{{ step }} / 3</span>
      </div>

      <!-- ─── Passo 1: Login do operador ─── -->
      <template v-if="step === 1">
        <div class="login-header">
          <h2 class="login-title">Configuração do Totem</h2>
          <p class="login-subtitle">Entre com sua conta SimplesFique para configurar este terminal.</p>
        </div>

        <form class="login-form" @submit.prevent="submitLogin">
          <div class="field-group">
            <label class="field-label">E-mail</label>
            <input
              v-model="email"
              type="email"
              class="field-input"
              placeholder="operador@empresa.com"
              autocomplete="email"
              required
            />
          </div>
          <div class="field-group">
            <label class="field-label">Senha</label>
            <input
              v-model="senha"
              type="password"
              class="field-input"
              placeholder="••••••••"
              autocomplete="current-password"
              required
            />
          </div>
          <p v-if="erro" class="form-error">{{ erro }}</p>
          <button class="btn-primary" type="submit" :disabled="loading">
            <span v-if="loading" class="btn-spinner"></span>
            {{ loading ? 'Entrando...' : 'Entrar' }}
          </button>
        </form>
      </template>

      <!-- ─── Passo 2: Selecionar terminal ─── -->
      <template v-else-if="step === 2">
        <div class="login-header">
          <h2 class="login-title">Selecione o Terminal</h2>
          <p class="login-subtitle">Escolha o terminal que representa este totem.</p>
        </div>

        <div v-if="loadingTerminais" class="loading-row">
          <span class="btn-spinner"></span>
          <span>Carregando terminais...</span>
        </div>

        <div v-else-if="terminais.length === 0" class="empty-state">
          Nenhum terminal ativo encontrado.
        </div>

        <div v-else class="terminal-list">
          <button
            v-for="t in terminais"
            :key="t.id"
            class="terminal-card"
            type="button"
            @click="selecionarTerminal(t)"
          >
            <span class="terminal-name">{{ t.nome }}</span>
            <span class="terminal-code">{{ t.codigo }}</span>
          </button>
        </div>

        <p v-if="erro" class="form-error">{{ erro }}</p>
      </template>

      <!-- ─── Passo 3: Senha operacional ─── -->
      <template v-else-if="step === 3">
        <div class="login-header">
          <h2 class="login-title">Senha Operacional</h2>
          <p class="login-subtitle">Terminal: <strong>{{ terminalSelecionado?.nome }}</strong></p>
        </div>

        <form class="login-form" @submit.prevent="submitSenha">
          <div class="field-group">
            <label class="field-label">Senha</label>
            <input
              v-model="senhaOperacional"
              type="password"
              class="field-input"
              placeholder="Senha operacional"
              autocomplete="off"
              required
            />
          </div>
          <p v-if="erro" class="form-error">{{ erro }}</p>
          <button class="btn-primary" type="submit" :disabled="loading">
            <span v-if="loading" class="btn-spinner"></span>
            {{ loading ? 'Confirmando...' : 'Confirmar' }}
          </button>
          <button class="btn-secondary" type="button" @click="voltarParaPasso2">
            Voltar
          </button>
        </form>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { useCompanyStore } from '@/stores/company'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'
import { useCatalogStore } from '@/stores/catalog'

const router = useRouter()
const admin = useAdminStore()
const company = useCompanyStore()
const sfique = useSimpleSfiqueStore()
const catalog = useCatalogStore()

const step = ref(1)
const loading = ref(false)
const erro = ref('')

// Passo 1
const email = ref('')
const senha = ref('')
const loginIdSaas = ref(null)
const loginIdEmpresa = ref(null)
const loginEmpresa = ref(null)

// Passo 2
const terminais = ref([])
const loadingTerminais = ref(false)
const terminalSelecionado = ref(null)

// Passo 3
const senhaOperacional = ref('')

async function submitLogin() {
  erro.value = ''
  loading.value = true
  try {
    const loginData = await sfique.login(email.value, senha.value)
    // SimpleSfique pode retornar a empresa em .empresa ou .empresas[0]
    const empresaObj = loginData?.empresa || loginData?.empresas?.[0] || null
    loginIdSaas.value = loginData?.saas?.id ?? loginData?.saas?.id_saas ?? loginData?.id_saas ?? null
    loginIdEmpresa.value = empresaObj?.id_empresa ?? empresaObj?.id ?? loginData?.id_empresa ?? null
    loginEmpresa.value = empresaObj
    await carregarTerminais()
    step.value = 2
  } catch (err) {
    erro.value = err.message || 'Falha ao autenticar. Verifique e-mail e senha.'
  } finally {
    loading.value = false
  }
}

async function carregarTerminais() {
  loadingTerminais.value = true
  erro.value = ''
  try {
    const lista = await sfique.listarTerminais()
    terminais.value = lista || []
  } catch (err) {
    erro.value = err.message || 'Erro ao listar terminais.'
    terminais.value = []
  } finally {
    loadingTerminais.value = false
  }
}

function selecionarTerminal(terminal) {
  terminalSelecionado.value = terminal
  erro.value = ''
  step.value = 3
}

function voltarParaPasso2() {
  erro.value = ''
  senhaOperacional.value = ''
  step.value = 2
}

async function submitSenha() {
  if (!terminalSelecionado.value) return
  erro.value = ''
  loading.value = true
  try {
    await sfique.validarSenha(terminalSelecionado.value.id, senhaOperacional.value)
    await sfique.carregarConfig(true)
    await catalog.fetchCatalog(true)

    // Persiste credenciais no backend para relogin automático e restart sem login
    await sfique.persistirSessao({
      email: email.value,
      senhaSimples: senha.value,
      senhaTerminal: senhaOperacional.value,
      idSaas: loginIdSaas.value,
      idEmpresa: loginIdEmpresa.value,
      empresa: loginEmpresa.value,
    })

    admin.markAuthenticated(terminalSelecionado.value.nome)
    company.markConfigured()

    router.replace({ name: 'home' })
  } catch (err) {
    erro.value = err.message || 'Senha inválida. Tente novamente.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (sfique.isConfigured) {
    router.replace({ name: 'home' })
    return
  }
  if (sfique.isAuthenticated) {
    carregarTerminais()
    step.value = 2
  }
})
</script>

<style scoped>
.totem-login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef9f5 0%, #fef5f0 50%, #fdeee7 100%);
  padding: var(--space-xl);
}

.login-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
  width: 100%;
  max-width: 440px;
  padding: var(--space-2xl);
  background: rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 60px rgba(245, 124, 0, 0.15);
}

.step-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e2e8f0;
  transition: background 0.3s;
}

.step-dot.active {
  background: var(--color-primary, #f57c00);
}

.step-dot.done {
  background: #4caf50;
}

.step-label {
  margin-left: auto;
  font-size: var(--font-size-sm);
  color: #94a3b8;
  font-weight: 600;
}

.login-header {
  text-align: center;
}

.login-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  margin: 0;
}

.login-subtitle {
  margin-top: var(--space-md);
  color: #64748b;
  line-height: 1.5;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.field-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #374151;
}

.field-input {
  padding: var(--space-md) var(--space-lg);
  border: 2px solid #e2e8f0;
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  color: #0f172a;
  background: #f8fafc;
  transition: border-color 0.2s;
  outline: none;
}

.field-input:focus {
  border-color: var(--color-primary, #f57c00);
  background: #fff;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  min-height: var(--btn-min-height, 52px);
  padding: var(--space-md) var(--space-xl);
  background: var(--color-primary, #f57c00);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  min-height: var(--btn-min-height, 52px);
  padding: var(--space-md) var(--space-xl);
  background: transparent;
  color: #64748b;
  border: 2px solid #e2e8f0;
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-secondary:hover {
  background: #f8fafc;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-error {
  color: #ef4444;
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: var(--space-sm) var(--space-md);
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.loading-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  color: #64748b;
  font-weight: 600;
}

.loading-row .btn-spinner {
  border-color: rgba(100, 116, 139, 0.3);
  border-top-color: #64748b;
}

.empty-state {
  text-align: center;
  color: #94a3b8;
  font-size: var(--font-size-md);
  padding: var(--space-xl) 0;
}

.terminal-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.terminal-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-xl);
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s, background 0.2s;
}

.terminal-card:hover {
  border-color: var(--color-primary, #f57c00);
  background: #fff;
}

.terminal-name {
  font-size: var(--font-size-md);
  font-weight: 700;
  color: #0f172a;
}

.terminal-code {
  font-size: var(--font-size-sm);
  color: #94a3b8;
  font-weight: 500;
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
