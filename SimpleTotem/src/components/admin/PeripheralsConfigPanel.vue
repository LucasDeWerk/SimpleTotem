<template>
  <div class="periph" :class="{ 'periph--embedded': embedded }">
    <div v-if="erroGlobal" class="periph-alert periph-alert--erro">
      <strong>Backend indisponível ou desatualizado.</strong>
      <span>{{ erroGlobal }}</span>
      <small>Reinicie o backend: <code>cd SimpleTotem-backend && python3 main.py</code></small>
    </div>

    <p v-if="showUsbScan" class="periph-intro">
      Conecte qualquer impressora, pinpad ou leitor USB. Escaneie os dispositivos e escolha o papel —
      funciona com qualquer marca (Bematech, Epson, Gertec, Ingenico, etc.).
    </p>
    <p v-else class="periph-intro">
      Status dos periféricos configurados no totem. Para atribuir ou trocar dispositivos USB,
      use a tela de configuração.
    </p>

    <!-- Papéis atribuídos -->
    <div class="periph-roles">
      <article
        v-for="cat in categoriasComStatus"
        :key="cat.id"
        class="periph-role"
        :class="`periph-role--${cat.badge}`"
      >
        <div class="periph-role__head">
          <span class="periph-role__icon">{{ cat.icon }}</span>
          <div>
            <h3>{{ cat.label }}</h3>
            <span class="periph-badge" :class="`periph-badge--${cat.badge}`">
              {{ labelBadge(cat.badge) }}
            </span>
          </div>
        </div>

        <template v-if="cat.configurado">
          <p class="periph-role__nome">{{ cat.configurado.nome }}</p>
          <code class="periph-vid">{{ cat.configurado.vendor_id }}:{{ cat.configurado.product_id }}</code>
          <p v-if="cat.detalhes?.caminho_usb" class="periph-detail">{{ cat.detalhes.caminho_usb }}</p>
          <p v-if="cat.detalhes?.porta_configurada" class="periph-detail">
            Porta {{ cat.detalhes.porta_configurada }}
          </p>
        </template>
        <p v-else class="periph-role__empty">Nenhum dispositivo atribuído</p>

        <div class="periph-role__actions">
          <button
            v-if="cat.temTeste && cat.configurado"
            class="periph-btn periph-btn--ghost"
            :disabled="testandoImpressao"
            @click="testarImpressao"
          >
            {{ testandoImpressao ? 'Imprimindo...' : 'Testar impressão' }}
          </button>
          <button
            v-if="cat.configurado"
            class="periph-btn periph-btn--danger"
            @click="remover(cat.id)"
          >
            Remover
          </button>
        </div>

        <p v-if="cat.dica_permissao" class="periph-hint">
          <code>{{ cat.dica_permissao }}</code>
        </p>
        <p
          v-if="mensagens[cat.id]"
          class="periph-msg"
          :class="mensagens[cat.id].tipo === 'ok' ? 'periph-msg--ok' : 'periph-msg--erro'"
        >
          {{ mensagens[cat.id].texto }}
        </p>
        <p
          v-if="cat.id === 'impressora' && resultadoTeste"
          class="periph-msg"
          :class="resultadoTeste.tipo === 'ok' ? 'periph-msg--ok' : 'periph-msg--erro'"
        >
          {{ resultadoTeste.texto }}
        </p>
      </article>
    </div>

    <!-- Ações resumo (só no painel admin) -->
    <div v-if="!showUsbScan" class="periph-toolbar">
      <button class="periph-btn periph-btn--secondary" :disabled="carregando" @click="atualizar">
        {{ carregando ? 'Atualizando...' : 'Atualizar status' }}
      </button>
      <button class="periph-btn periph-btn--primary periph-btn--with-icon" @click="irConfigurar">
        <span class="material-icons">usb</span>
        Configurar dispositivos USB
      </button>
    </div>

    <!-- USB — apenas na tela dedicada -->
    <div v-if="showUsbScan" class="periph-usb">
      <div class="periph-usb__head">
        <div>
          <h3>Dispositivos USB conectados</h3>
          <p>Selecione o papel de cada periférico plugado no totem</p>
        </div>
        <div class="periph-usb__btns">
          <button class="periph-btn periph-btn--secondary" :disabled="carregando" @click="atualizar">
            {{ carregando ? 'Atualizando...' : 'Atualizar status' }}
          </button>
          <button class="periph-btn periph-btn--primary" :disabled="carregando" @click="escanear">
            {{ carregando ? 'Escaneando...' : 'Escanear USB' }}
          </button>
        </div>
      </div>

      <p v-if="!electronDisponivel" class="periph-warn">
        Escaneamento USB só funciona no app Electron. Abra o totem pelo <code>npm run electron:dev</code>.
      </p>

      <p v-else-if="!dispositivosUSB.length" class="periph-usb__empty">
        Nenhum dispositivo listado. Clique em <strong>Escanear USB</strong>.
      </p>

      <div v-else class="periph-usb__list">
        <div v-for="(dev, i) in dispositivosUSB" :key="i" class="periph-usb__item">
          <div class="periph-usb__info">
            <strong>{{ dev.produto || 'Dispositivo USB' }}</strong>
            <span>{{ dev.fabricante || 'Fabricante desconhecido' }}</span>
            <code>{{ dev.vendorId }}:{{ dev.productId }}</code>
          </div>
          <div class="periph-usb__assign">
            <button
              v-for="cat in CATEGORIAS"
              :key="cat.id"
              class="periph-assign"
              :class="{ 'periph-assign--on': jaAtribuido(cat.id, dev) }"
              :disabled="configurando === `${cat.id}-${dev.vendorId}`"
              @click="atribuir(cat.id, dev)"
            >
              {{ jaAtribuido(cat.id, dev) ? '✓ ' : '' }}{{ cat.label }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHardwareAdmin, CATEGORIAS } from '@/composables/useHardwareAdmin'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  /** Escaneamento e atribuição USB — só na tela /admin/hardware */
  showUsbScan: { type: Boolean, default: false },
})

const router = useRouter()

const {
  carregando,
  configurando,
  testandoImpressao,
  mensagens,
  resultadoTeste,
  dispositivosUSB,
  erroGlobal,
  categoriasComStatus,
  labelBadge,
  jaAtribuido,
  carregarTudo,
  buscarUSB,
  atribuir,
  remover,
  testarImpressao,
} = useHardwareAdmin()

const electronDisponivel = computed(() => Boolean(window.hardwareAPI?.listarUSB))

async function atualizar() {
  await carregarTudo()
}

async function escanear() {
  await buscarUSB()
}

function irConfigurar() {
  router.push({ name: 'admin-hardware' })
}

onMounted(async () => {
  await carregarTudo()
  if (props.showUsbScan && electronDisponivel.value) {
    await buscarUSB()
  }
})

defineExpose({ carregarTudo, buscarUSB })
</script>

<style scoped>
.periph {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.periph-intro {
  margin: 0;
  color: #64748b;
  font-size: 0.92rem;
  line-height: 1.5;
}

.periph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.periph-btn--with-icon {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.periph-btn--with-icon .material-icons {
  font-size: 1.15rem;
}

.periph-alert {
  padding: 0.85rem 1rem;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.88rem;
}

.periph-alert--erro {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.periph-alert code {
  font-size: 0.78rem;
  background: rgba(0, 0, 0, 0.06);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
}

.periph-warn {
  margin: 0;
  padding: 0.75rem 1rem;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  color: #9a3412;
  font-size: 0.85rem;
}

.periph-roles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.85rem;
}

.periph-role {
  background: #fff;
  border: 1px solid rgba(245, 124, 0, 0.12);
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  box-shadow: 0 2px 8px rgba(245, 124, 0, 0.06);
}

.periph-role--ok { border-left: 4px solid #22c55e; }
.periph-role--sem_permissao { border-left: 4px solid #f97316; }
.periph-role--desconectado { border-left: 4px solid #eab308; }
.periph-role--pendente { border-left: 4px solid #94a3b8; }

.periph-role__head {
  display: flex;
  gap: 0.65rem;
  align-items: flex-start;
}

.periph-role__icon { font-size: 1.6rem; line-height: 1; }

.periph-role h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}

.periph-badge {
  display: inline-block;
  margin-top: 0.2rem;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.periph-badge--ok { background: #dcfce7; color: #166534; }
.periph-badge--sem_permissao { background: #ffedd5; color: #9a3412; }
.periph-badge--desconectado { background: #fef9c3; color: #854d0e; }
.periph-badge--pendente { background: #f1f5f9; color: #475569; }

.periph-role__nome {
  margin: 0;
  font-weight: 700;
  color: #0f172a;
  font-size: 0.92rem;
}

.periph-vid,
.periph-usb__info code {
  font-family: ui-monospace, monospace;
  font-size: 0.78rem;
  color: #64748b;
}

.periph-detail {
  margin: 0;
  font-size: 0.8rem;
  color: #94a3b8;
}

.periph-role__empty {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

.periph-role__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.25rem;
}

.periph-usb {
  background: #fff;
  border: 1px solid rgba(245, 124, 0, 0.12);
  border-radius: 12px;
  padding: 1rem;
}

.periph-usb__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.periph-usb__head h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}

.periph-usb__head p {
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  color: #64748b;
}

.periph-usb__btns {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.periph-usb__empty {
  text-align: center;
  color: #94a3b8;
  padding: 1.5rem;
  font-size: 0.9rem;
}

.periph-usb__list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.periph-usb__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem;
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.1);
  border-radius: 10px;
  flex-wrap: wrap;
}

.periph-usb__info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 160px;
}

.periph-usb__info span {
  font-size: 0.82rem;
  color: #64748b;
}

.periph-usb__assign {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.periph-assign {
  border: 1px solid rgba(245, 124, 0, 0.25);
  background: #fff;
  color: #c2410c;
  border-radius: 8px;
  padding: 0.4rem 0.7rem;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}

.periph-assign:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.08);
}

.periph-assign--on {
  background: #dcfce7;
  border-color: #22c55e;
  color: #166534;
}

.periph-assign:disabled {
  opacity: 0.55;
  cursor: wait;
}

.periph-btn {
  border: none;
  border-radius: 8px;
  padding: 0.5rem 0.9rem;
  font-weight: 700;
  font-size: 0.84rem;
  cursor: pointer;
}

.periph-btn--primary {
  background: linear-gradient(135deg, #f57c00, #e27602);
  color: #fff;
}

.periph-btn--secondary {
  background: rgba(245, 124, 0, 0.08);
  color: #c2410c;
  border: 1px solid rgba(245, 124, 0, 0.2);
}

.periph-btn--ghost {
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #475569;
}

.periph-btn--danger {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.periph-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.periph-hint {
  margin: 0;
  font-size: 0.72rem;
  color: #9a3412;
  background: #fff7ed;
  padding: 0.45rem 0.55rem;
  border-radius: 6px;
  word-break: break-all;
}

.periph-msg {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 600;
}

.periph-msg--ok { color: #15803d; }
.periph-msg--erro { color: #b91c1c; }

@media (max-width: 640px) {
  .periph-usb__item {
    flex-direction: column;
    align-items: stretch;
  }
  .periph-usb__assign {
    flex-direction: column;
  }
  .periph-assign {
    width: 100%;
    text-align: center;
  }
}
</style>
