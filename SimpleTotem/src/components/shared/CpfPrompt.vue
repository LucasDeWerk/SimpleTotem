<template>
  <div class="cpf-overlay">
    <div class="cpf-card">
      <h3 class="cpf-title">CPF na nota?</h3>
      <p v-if="obrigatorio" class="cpf-hint">Vendas acima de R$ 999,00 exigem CPF.</p>

      <div class="cpf-display" :class="{ invalid: erro }">{{ formatado || '000.000.000-00' }}</div>
      <p v-if="erro" class="cpf-error">{{ erro }}</p>

      <div class="cpf-keypad">
        <button v-for="n in ['1','2','3','4','5','6','7','8','9']" :key="n" type="button" @click="digitar(n)">{{ n }}</button>
        <button type="button" @click="limpar">C</button>
        <button type="button" @click="digitar('0')">0</button>
        <button type="button" @click="apagar">⌫</button>
      </div>

      <div class="cpf-actions">
        <button class="cpf-confirm" type="button" @click="confirmar">Confirmar</button>
        <button v-if="!obrigatorio" class="cpf-skip" type="button" @click="$emit('confirm', null)">Sem CPF</button>
        <button class="cpf-skip" type="button" @click="$emit('cancel')">Voltar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { cpfValido, formatarCpf } from '@/utils/cpf'

defineProps({ obrigatorio: { type: Boolean, default: false } })
const emit = defineEmits(['confirm', 'cancel'])

const digitos = ref('')
const erro = ref('')
const formatado = computed(() => formatarCpf(digitos.value))

function digitar(n) {
  if (digitos.value.length < 11) digitos.value += n
  erro.value = ''
}
function apagar() { digitos.value = digitos.value.slice(0, -1); erro.value = '' }
function limpar() { digitos.value = ''; erro.value = '' }

function confirmar() {
  if (!cpfValido(digitos.value)) {
    erro.value = 'CPF inválido. Confira os números.'
    return
  }
  emit('confirm', digitos.value)
}
</script>

<style scoped>
.cpf-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; z-index: 50; }
.cpf-card { background: var(--bg-color); border-radius: 20px; padding: 28px; width: min(480px, 92vw); text-align: center; box-shadow: var(--shadow-lg); }
.cpf-title { font-size: 1.6rem; margin: 0 0 8px; color: var(--text-color); }
.cpf-hint { color: var(--color-warning); margin: 0 0 8px; }
.cpf-display { font-size: 2rem; letter-spacing: 2px; padding: 14px; border: 2px solid var(--color-border); border-radius: 12px; margin: 12px 0; color: var(--text-color); }
.cpf-display.invalid { border-color: var(--color-error); }
.cpf-error { color: var(--color-error); margin: 0 0 8px; }
.cpf-keypad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px; }
.cpf-keypad button { font-size: 1.8rem; padding: 18px 0; border-radius: 14px; border: 1px solid var(--color-border); background: var(--bg-card); color: var(--text-color); }
.cpf-keypad button:active { background: var(--color-primary-light); }
.cpf-actions { display: flex; flex-direction: column; gap: 8px; }
.cpf-confirm { font-size: 1.3rem; padding: 16px; border: 0; border-radius: 14px; background: var(--color-primary); color: #fff; }
.cpf-skip { font-size: 1.1rem; padding: 12px; border: 0; background: transparent; color: var(--text-color); }
</style>
