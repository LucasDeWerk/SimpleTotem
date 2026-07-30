import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  sfLogin,
  sfListarTerminais,
  sfValidarSenha,
  sfObterConfig,
  sfEmitirCupom,
  setSfiqueTokenRefresher,
  obterSessaoTotem,
  salvarSessaoTotem,
  salvarEmpresaSimpleSfique,
  reloginSfique,
} from '@/services/api'

export const useSimpleSfiqueStore = defineStore('simplesfique', () => {
  const jwtToken = ref('')
  const terminalToken = ref('')
  const terminalId = ref('')
  const terminalInfo = ref(null)

  const configVersion = ref(0)
  const produtosVersion = ref(0)

  const emiteCupomFiscal = ref(false)
  const ambientes = ref([])
  const menus = ref([])
  const menuProdutos = ref([])

  // Controle de hidratação — garante que tentamos restaurar sessão apenas 1x por startup
  const hydrateAttempted = ref(false)

  // Legado — painel admin (sync local), não usado no fluxo do totem
  const sessao = ref(null)

  const isAuthenticated = computed(() => Boolean(jwtToken.value))
  const isConfigured = computed(() => Boolean(terminalToken.value && terminalId.value))

  function applyConfigData(data) {
    ambientes.value = data.ambientes || []
    menus.value = data.menus || []
    menuProdutos.value = data.menu_produtos || []
    terminalInfo.value = data.terminal || terminalInfo.value
    emiteCupomFiscal.value = Boolean(data.terminal?.emite_cupom_fiscal)

    if (data.config_version != null) configVersion.value = data.config_version
    if (data.produtos_version != null) produtosVersion.value = data.produtos_version
  }

  // ── Login e setup ────────────────────────────────────────────────────────────

  async function login(email, senha) {
    const data = await sfLogin(email, senha)
    jwtToken.value = data.token || ''
    return data
  }

  async function listarTerminais() {
    return sfListarTerminais(jwtToken.value)
  }

  async function validarSenha(id, senha) {
    const data = await sfValidarSenha(id, senha, jwtToken.value)
    terminalToken.value = data.access_token || ''
    terminalId.value = String(id)
    terminalInfo.value = data.terminal || null
    return data
  }

  async function carregarConfig(force = false) {
    const cv = force ? 0 : configVersion.value
    const pv = force ? 0 : produtosVersion.value
    const data = await sfObterConfig(terminalId.value, cv, pv, terminalToken.value)

    if (data?.config_version != null) configVersion.value = data.config_version
    if (data?.produtos_version != null) produtosVersion.value = data.produtos_version

    if (data?.updated) {
      applyConfigData(data)
      return true
    }

    return false
  }

  async function emitirCupom(cupomId) {
    return sfEmitirCupom(cupomId, jwtToken.value)
  }

  // ── Persistência de sessão no backend ───────────────────────────────────────

  /**
   * Chamado após o login de 3 passos. Salva todos os tokens e senhas
   * (criptografadas) no backend para que o totem não precise fazer login
   * novamente nos próximos starts.
   */
  async function persistirSessao({ email, senhaSimples, senhaTerminal, idSaas, idEmpresa, empresa }) {
    try {
      await salvarSessaoTotem({
        email,
        senha_simples: senhaSimples,
        terminal_id: Number(terminalId.value),
        terminal_token: terminalToken.value,
        senha_terminal: senhaTerminal,
        jwt_token: jwtToken.value,
        id_saas: idSaas ?? null,
        id_empresa: idEmpresa ?? null,
      })
      console.log('[Sfique] Sessão persistida no backend')
    } catch (err) {
      console.warn('[Sfique] Falha ao persistir sessão (não crítico):', err.message)
    }

    // Salva a empresa no banco local para que o CNPJ fique disponível para pagamentos
    if (empresa) {
      try {
        await salvarEmpresaSimpleSfique(empresa)
        console.log('[Sfique] Empresa salva no banco local')
      } catch (err) {
        console.warn('[Sfique] Falha ao salvar empresa (não crítico):', err.message)
      }
    }
  }

  /**
   * Chamado uma única vez no startup (pelo router guard).
   * Tenta restaurar tokens do backend para que o login não seja necessário.
   */
  async function hydrateFromBackend() {
    if (hydrateAttempted.value) return
    hydrateAttempted.value = true
    try {
      const dados = await obterSessaoTotem()
      if (dados?.configurado && dados.terminal_token && dados.terminal_id) {
        jwtToken.value = dados.jwt_token || ''
        terminalToken.value = dados.terminal_token
        terminalId.value = String(dados.terminal_id)
        console.log('[Sfique] Sessão restaurada do backend — terminal:', dados.terminal_id)
        // JWT vazio (token expirado ou não gravado) → renova agora para não bloquear na próxima chamada
        if (!jwtToken.value) {
          console.warn('[Sfique] JWT ausente no banco — relogin proativo')
          await reloginAutomatico()
        }
      }
    } catch (err) {
      console.warn('[Sfique] Erro ao hidratar sessão:', err.message)
    }
  }

  /**
   * Renovação automática de tokens via backend (usando credenciais salvas).
   * Retorna { jwt_token, terminal_token } ou null em caso de falha.
   * Registrado em api.js como callback de retry em 401.
   */
  async function reloginAutomatico() {
    try {
      const dados = await reloginSfique()
      if (!dados) return null
      jwtToken.value = dados.jwt_token || ''
      terminalToken.value = dados.terminal_token || ''
      console.log('[Sfique] Tokens renovados automaticamente')
      return dados
    } catch (err) {
      console.warn('[Sfique] Falha no relogin automático:', err.message)
      return null
    }
  }

  // Registra o callback de refresh — ativo para toda a vida do app
  setSfiqueTokenRefresher(reloginAutomatico)

  // ── Legado ───────────────────────────────────────────────────────────────────

  function setSessao(data) {
    sessao.value = data
  }

  async function hydrate() {
    return sessao.value
  }

  function logout() {
    jwtToken.value = ''
    terminalToken.value = ''
    terminalId.value = ''
    terminalInfo.value = null
    configVersion.value = 0
    produtosVersion.value = 0
    emiteCupomFiscal.value = false
    ambientes.value = []
    menus.value = []
    menuProdutos.value = []
    sessao.value = null
    hydrateAttempted.value = false
  }

  return {
    sessao,
    jwtToken,
    terminalToken,
    terminalId,
    terminalInfo,
    configVersion,
    produtosVersion,
    emiteCupomFiscal,
    ambientes,
    menus,
    menuProdutos,
    hydrateAttempted,
    isAuthenticated,
    isConfigured,
    login,
    listarTerminais,
    validarSenha,
    carregarConfig,
    emitirCupom,
    hydrateFromBackend,
    persistirSessao,
    reloginAutomatico,
    setSessao,
    hydrate,
    logout,
  }
})
