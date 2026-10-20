<template>
  <div class="ticket-panel">
    <p class="hint">Leia o QR do ticket com o leitor (ou digite o código) e confirme. Cada ticket só pode ser usado uma vez.</p>

    <form class="ticket-form" @submit.prevent="validar">
      <input
        ref="campo"
        v-model.trim="codigo"
        type="text"
        autocomplete="off"
        placeholder="Código do ticket (UUID)"
        :disabled="validando"
      />
      <button class="btn-primary" type="submit" :disabled="validando || !codigo">
        {{ validando ? 'Validando...' : 'Validar ticket' }}
      </button>
    </form>

    <p v-if="resultado" class="feedback feedback--ok">
      ✓ Ticket validado — {{ Number(resultado.quantidade) }} unidade(s) liberada(s).
    </p>
    <p v-if="erro" class="feedback feedback--error">{{ erro }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { sfValidarTicket } from '@/services/api'

const codigo = ref('')
const validando = ref(false)
const resultado = ref(null)
const erro = ref('')
const campo = ref(null)

onMounted(() => campo.value?.focus())

async function validar() {
  validando.value = true
  resultado.value = null
  erro.value = ''
  try {
    const r = await sfValidarTicket(codigo.value)
    resultado.value = r.ticket
    codigo.value = ''
  } catch (err) {
    erro.value = err.message || 'Falha ao validar o ticket'
  } finally {
    validando.value = false
    campo.value?.focus()
  }
}
</script>

<style scoped>
.hint { color: var(--text-color); opacity: .75; margin: 0 0 12px; }
.ticket-form { display: flex; gap: 10px; flex-wrap: wrap; }
.ticket-form input { flex: 1 1 280px; padding: 12px; font-size: 1rem; border: 1px solid var(--color-border); border-radius: 8px; background: var(--bg-color); color: var(--text-color); }
.btn-primary { padding: 12px 20px; border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; font-size: 1rem; }
.btn-primary:disabled { opacity: .5; }
.feedback { margin-top: 14px; font-size: 1.05rem; }
.feedback--ok { color: var(--color-success); }
.feedback--error { color: var(--color-error); }
</style>
