<template>
  <div class="menu-admin-panel">
    <div class="menu-admin-intro">
      <span class="material-icons intro-icon">sync_alt</span>
      <div>
        <p class="intro-title">Canal direto com a Fiserv</p>
        <p class="intro-desc">
          Abre o Menu Administrativo do pinpad — a mesma tela usada para diagnóstico,
          testes de comunicação e manutenção — espelhada aqui para acompanhar e
          responder com mais conforto do que direto no aparelho.
        </p>
      </div>
    </div>

    <button
      v-if="podeAbrir"
      class="btn-primary btn-abrir"
      type="button"
      :disabled="executando"
      @click="iniciar"
    >
      <span class="material-icons">terminal</span>
      Abrir Menu Administrativo
    </button>

    <p v-if="erroInicio" class="feedback feedback--error">{{ erroInicio }}</p>

    <div v-if="execucaoId" class="sessao">
      <div class="sessao-status" :class="`sessao-status--${statusClasse}`">
        <span class="status-dot" :class="{ 'status-dot--pulsando': status === 'processando' }"></span>
        <span>{{ statusLabel }}</span>
      </div>

      <div class="timeline" ref="timelineEl">
        <p v-if="linhas.length === 0" class="timeline-vazio">Conectando com o pinpad...</p>

        <div
          v-for="(linha, idx) in linhas"
          :key="idx"
          class="timeline-item"
          :class="`timeline-item--${linha.tipo}`"
        >
          <span class="material-icons timeline-icon">{{ linha.icone }}</span>
          <div class="timeline-corpo">
            <template v-if="linha.tipo === 'prompt'">
              <strong>{{ tipoPromptLabel(linha.tipo_prompt) }}</strong>
              <p v-if="linha.mensagem" class="timeline-detalhe">{{ linha.mensagem }}</p>
              <ul v-if="linha.opcoes && linha.opcoes.length" class="timeline-opcoes">
                <li v-for="op in linha.opcoes" :key="op.indice">{{ op.label }}</li>
              </ul>
            </template>
            <template v-else>
              <span>{{ linha.texto }}</span>
              <span v-if="linha.repeticoes > 1" class="timeline-contador">×{{ linha.repeticoes }}</span>

              <div v-if="linha.progresso" class="timeline-progresso">
                <div class="progresso-barra">
                  <div class="progresso-preenchido" :style="{ width: linha.progresso.percentual + '%' }"></div>
                </div>
                <span class="progresso-texto">{{ linha.progresso.atual }}/{{ linha.progresso.total }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div
        v-if="resultadoFinal"
        class="resultado-banner"
        :class="resultadoFinal.aprovada ? 'resultado-banner--ok' : 'resultado-banner--alerta'"
      >
        <span class="material-icons">{{ resultadoFinal.aprovada ? 'check_circle' : 'warning' }}</span>
        <span>Sessão encerrada — {{ resultadoFinal.mensagem_resultado || `código ${resultadoFinal.resultado}` }}</span>
      </div>

      <div v-if="promptPendente" class="acao-pendente">
        <p class="acao-pergunta">{{ promptPendente.mensagem || tipoPromptLabel(promptPendente.tipo_prompt) }}</p>

        <div v-if="promptPendente.tipo_prompt === 'menu'" class="acao-menu">
          <button
            v-for="op in promptPendente.opcoes"
            :key="op.indice"
            class="opcao-btn"
            type="button"
            :disabled="respondendo"
            @click="responder(op.indice)"
          >
            {{ op.label }}
          </button>
        </div>

        <div v-else-if="promptPendente.tipo_prompt === 'confirmacao'" class="acao-simnao">
          <!-- Protocolo CliSiTef (cmd=20): "0" confirma, qualquer outro valor recusa —
               mesma convenção já validada em hardware real nos loops de transação/cancelamento. -->
          <button class="btn-primary" type="button" :disabled="respondendo" @click="responder('0')">
            <span class="material-icons">check</span> Sim
          </button>
          <button class="btn-secondary" type="button" :disabled="respondendo" @click="responder('1')">
            <span class="material-icons">close</span> Não
          </button>
        </div>

        <div v-else class="acao-dado">
          <input
            v-model="respostaTexto"
            :type="ehCampoSenha(promptPendente.tipo_prompt) ? 'password' : 'text'"
            autocomplete="off"
            placeholder="Digite aqui"
            @keyup.enter="enviarResposta"
          />
          <button class="btn-primary" type="button" :disabled="respondendo || !respostaTexto" @click="enviarResposta">
            Enviar
          </button>
        </div>
      </div>

      <p v-if="erroResposta" class="feedback feedback--error">{{ erroResposta }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, nextTick } from 'vue'
import { iniciarFuncaoAdmin, obterStatusFuncaoAdmin, responderFuncaoAdmin } from '@/services/api'

const execucaoId = ref(null)
const executando = ref(false)
const mensagens = ref([])
const promptPendente = ref(null)
const status = ref('')
const erroInicio = ref('')
const erroResposta = ref('')
const respostaTexto = ref('')
const respondendo = ref(false)
const timelineEl = ref(null)

let pollTimer = null

const podeAbrir = computed(() => !execucaoId.value || status.value === 'finalizada' || status.value === 'erro')

const statusLabel = computed(() => {
  if (status.value === 'finalizada') return 'Finalizado'
  if (status.value === 'erro') return 'Erro'
  return 'Conectado — em andamento'
})

const statusClasse = computed(() => {
  if (status.value === 'finalizada') return 'ok'
  if (status.value === 'erro') return 'erro'
  return 'ativo'
})

function tipoPromptLabel(tipo) {
  const labels = {
    menu: 'Escolha uma opção',
    confirmacao: 'Confirmação',
    dado: 'Dado solicitado',
    senha_supervisor: 'Senha do supervisor',
    campo_mascarado: 'Campo protegido',
  }
  return labels[tipo] || tipo
}

function ehCampoSenha(tipo) {
  return tipo === 'senha_supervisor' || tipo === 'campo_mascarado'
}

function iconePara(tipo) {
  if (tipo === 'info') return 'info'
  if (tipo === 'mensagem') return 'chat_bubble'
  if (tipo === 'prompt') return 'help'
  if (tipo === 'erro') return 'error'
  return 'circle'
}

// Mensagens tipo "Atualizando Reg. 5/212" ou "Aguarde, processando...(35)" chegam
// aos montes, quase idênticas, e viravam uma linha nova cada uma — uma parede de
// texto repetido. Aqui a gente extrai o "miolo" da frase (sem o contador/sufixo
// numérico do final) pra decidir se é a MESMA mensagem evoluindo, e nesse caso
// atualiza a linha existente em vez de empilhar uma nova.
function baseTexto(texto) {
  if (!texto) return ''
  return texto.replace(/[\s:()./\d]+$/, '').trim()
}

function extrairProgresso(texto) {
  const m = (texto || '').match(/(\d+)\s*\/\s*(\d+)\s*$/)
  if (!m) return null
  const atual = Number(m[1])
  const total = Number(m[2])
  if (!total) return null
  return { atual, total, percentual: Math.min(100, Math.round((atual / total) * 100)) }
}

const linhas = computed(() => {
  const resultado = []
  for (const msg of mensagens.value) {
    if (msg.tipo === 'resultado') continue // mostrado à parte, no banner final

    if (msg.tipo === 'prompt') {
      resultado.push({ ...msg, icone: iconePara('prompt') })
      continue
    }

    if (msg.tipo === 'mensagem' || msg.tipo === 'info' || msg.tipo === 'erro') {
      const base = baseTexto(msg.texto)
      const anterior = resultado[resultado.length - 1]
      if (base && anterior && anterior.tipo === msg.tipo && anterior._base === base) {
        anterior.texto = msg.texto
        anterior.repeticoes = (anterior.repeticoes || 1) + 1
        anterior.progresso = extrairProgresso(msg.texto)
        continue
      }
      resultado.push({
        tipo: msg.tipo,
        texto: msg.texto,
        _base: base,
        repeticoes: 1,
        progresso: extrairProgresso(msg.texto),
        icone: iconePara(msg.tipo),
      })
      continue
    }

    resultado.push({ ...msg, icone: iconePara(msg.tipo) })
  }
  return resultado
})

const resultadoFinal = computed(() => mensagens.value.find(m => m.tipo === 'resultado') || null)

async function rolarParaFinal() {
  await nextTick()
  if (timelineEl.value) {
    timelineEl.value.scrollTop = timelineEl.value.scrollHeight
  }
}

async function iniciar() {
  pararPoll()
  erroInicio.value = ''
  erroResposta.value = ''
  mensagens.value = []
  promptPendente.value = null
  status.value = 'processando'
  executando.value = true

  try {
    const resultado = await iniciarFuncaoAdmin('110')
    execucaoId.value = resultado.execucao_id
    pollTimer = setInterval(atualizarStatus, 1000)
    await atualizarStatus()
  } catch (err) {
    erroInicio.value = err.message || 'Erro ao conectar com o pinpad'
    executando.value = false
    status.value = 'erro'
  }
}

async function atualizarStatus() {
  if (!execucaoId.value) return
  try {
    const estado = await obterStatusFuncaoAdmin(execucaoId.value)
    mensagens.value = estado.mensagens || []
    promptPendente.value = estado.prompt_pendente || null
    status.value = estado.status

    if (estado.status === 'finalizada' || estado.status === 'erro') {
      executando.value = false
      pararPoll()
    }
    await rolarParaFinal()
  } catch (err) {
    // Falha pontual de rede não deve interromper o polling.
    console.warn('[ComunicacaoFiserv] Erro ao consultar status:', err)
  }
}

async function responder(valor) {
  if (!execucaoId.value) return
  respondendo.value = true
  erroResposta.value = ''
  try {
    await responderFuncaoAdmin(execucaoId.value, valor)
    respostaTexto.value = ''
    await atualizarStatus()
  } catch (err) {
    erroResposta.value = err.message || 'Erro ao enviar resposta'
  } finally {
    respondendo.value = false
  }
}

function enviarResposta() {
  if (!respostaTexto.value) return
  responder(respostaTexto.value)
}

function pararPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onUnmounted(() => {
  pararPoll()
})
</script>

<style scoped>
.menu-admin-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.menu-admin-intro {
  display: flex;
  gap: var(--space-md);
  align-items: flex-start;
  background: rgba(245, 124, 0, 0.05);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.intro-icon {
  font-size: 2rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

.intro-title {
  margin: 0 0 0.25rem;
  font-weight: 700;
  color: #0f172a;
}

.intro-desc {
  margin: 0;
  color: #64748b;
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.feedback {
  margin: 0;
  font-weight: 600;
}

.feedback--error {
  color: #c62828;
}

.btn-abrir {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.sessao {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding-top: var(--space-md);
}

.sessao-status {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-weight: 700;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-full);
  width: fit-content;
}

.sessao-status--ativo {
  background: rgba(255, 152, 0, 0.12);
  color: #ff9800;
}

.sessao-status--ok {
  background: rgba(76, 175, 80, 0.12);
  color: #4caf50;
}

.sessao-status--erro {
  background: rgba(244, 67, 54, 0.12);
  color: #f44336;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.status-dot--pulsando {
  animation: pulsar 1.4s ease-in-out infinite;
}

@keyframes pulsar {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.75); }
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  max-height: 420px;
  overflow-y: auto;
  padding-right: 4px;
}

.timeline-vazio {
  margin: 0;
  color: #64748b;
  font-size: var(--font-size-sm);
}

.timeline-item {
  display: flex;
  gap: var(--space-sm);
  align-items: flex-start;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  background: rgba(245, 124, 0, 0.04);
}

.timeline-item--erro {
  background: rgba(244, 67, 54, 0.08);
}

.timeline-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
  color: var(--color-primary);
  margin-top: 0.1rem;
}

.timeline-item--erro .timeline-icon {
  color: #f44336;
}

.timeline-corpo {
  flex: 1;
  font-size: var(--font-size-sm);
  color: #0f172a;
  line-height: 1.4;
}

.timeline-detalhe {
  margin: 0.2rem 0 0;
  color: #475569;
  font-weight: 400;
}

.timeline-opcoes {
  margin: 0.35rem 0 0;
  padding-left: 1.1rem;
  color: #64748b;
}

.timeline-contador {
  margin-left: 0.4rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: #94a3b8;
}

.timeline-progresso {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: 0.35rem;
}

.progresso-barra {
  flex: 1;
  height: 6px;
  border-radius: var(--radius-full);
  background: rgba(245, 124, 0, 0.12);
  overflow: hidden;
}

.progresso-preenchido {
  height: 100%;
  background: linear-gradient(135deg, #F57C00, #E27602);
  border-radius: var(--radius-full);
  transition: width 0.2s ease-out;
}

.progresso-texto {
  font-size: 0.75rem;
  font-weight: 700;
  color: #94a3b8;
  white-space: nowrap;
}

.resultado-banner {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-md);
  font-weight: 700;
}

.resultado-banner--ok {
  background: rgba(76, 175, 80, 0.12);
  color: #2e7d32;
}

.resultado-banner--alerta {
  background: rgba(255, 152, 0, 0.12);
  color: #b26a00;
}

.acao-pendente {
  background: white;
  border: 2px solid rgba(245, 124, 0, 0.25);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: 0 2px 10px rgba(245, 124, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.acao-pergunta {
  margin: 0;
  font-weight: 700;
  color: #0f172a;
}

.acao-menu {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.opcao-btn {
  text-align: left;
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-md);
  border: 2px solid rgba(245, 124, 0, 0.2);
  background: rgba(245, 124, 0, 0.06);
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.opcao-btn:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.14);
  border-color: rgba(245, 124, 0, 0.4);
  transform: translateX(2px);
}

.opcao-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.acao-simnao {
  display: flex;
  gap: var(--space-md);
}

.acao-dado {
  display: flex;
  gap: var(--space-sm);
}

.acao-dado input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.15);
  border-color: rgba(245, 124, 0, 0.35);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
