<template>
  <div v-if="dataUrl" class="pix-qr">
    <img :src="dataUrl" alt="QR Code PIX" class="pix-qr-image" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import QRCode from 'qrcode'

const props = defineProps({
  payload: { type: String, default: '' }
})

const dataUrl = ref('')

watch(
  () => props.payload,
  async (value) => {
    if (!value) {
      dataUrl.value = ''
      return
    }
    try {
      dataUrl.value = await QRCode.toDataURL(value, {
        width: 280,
        margin: 2,
        errorCorrectionLevel: 'M',
      })
    } catch (err) {
      console.error('[PixQrCode] Erro ao gerar QR:', err)
      dataUrl.value = ''
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.pix-qr {
  display: flex;
  justify-content: center;
  padding: var(--space-md);
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.pix-qr-image {
  width: 280px;
  height: 280px;
  object-fit: contain;
}
</style>
