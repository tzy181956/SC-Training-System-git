<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'

import type { RuntimeAccessInfo } from '@/api/runtimeAccess'

const props = defineProps<{
  info: RuntimeAccessInfo
}>()

const copied = ref(false)
const qrDataUrl = ref('')

const accessHint = computed(() =>
  props.info.source === 'fallback' ? '当前访问地址（兜底显示）' : '同一网络下可直接访问',
)

const sourceLabel = computed(() => (props.info.source === 'fallback' ? '当前地址' : '推荐地址'))

async function buildQrCode() {
  qrDataUrl.value = await QRCode.toDataURL(props.info.accessUrl, {
    errorCorrectionLevel: 'M',
    margin: 1,
    width: 128,
  })
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(props.info.accessUrl)
    copied.value = true
    window.setTimeout(() => {
      copied.value = false
    }, 1600)
  } catch {
    copied.value = false
  }
}

watch(
  () => props.info.accessUrl,
  () => {
    buildQrCode()
  },
  { immediate: true },
)

onMounted(buildQrCode)
</script>

<template>
  <div class="access-card">
    <div class="access-copy">
      <div class="access-heading">
        <p class="eyebrow">{{ accessHint }}</p>
        <small class="source-label">{{ sourceLabel }}</small>
      </div>
      <a class="access-link" :href="info.accessUrl" target="_blank" rel="noreferrer">{{ info.accessUrl }}</a>
      <div class="access-actions">
        <button class="ghost-btn slim" type="button" @click="copyUrl">{{ copied ? '已复制' : '复制地址' }}</button>
        <small v-if="info.generatedAt" class="access-meta">生成时间：{{ info.generatedAt }}</small>
      </div>
    </div>
    <div class="qr-panel">
      <img v-if="qrDataUrl" :src="qrDataUrl" alt="训练模式访问二维码" class="qr-image" />
      <span>扫码进入</span>
    </div>
  </div>
</template>

<style scoped>
.access-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.access-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.access-heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  flex-wrap: wrap;
}

.eyebrow {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--text);
}

.source-label,
.access-meta,
.qr-panel {
  color: var(--muted);
}

.access-link {
  color: var(--primary);
  font-size: 0.98rem;
  font-weight: 700;
  line-height: 1.25;
  word-break: break-all;
}

.access-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.qr-panel {
  display: grid;
  justify-items: center;
  gap: 4px;
  text-align: center;
}

.qr-image {
  width: 84px;
  height: 84px;
  border-radius: 12px;
  background: white;
  padding: 6px;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

@media (max-width: 980px) {
  .access-card {
    grid-template-columns: 1fr;
    justify-items: start;
  }

  .qr-panel {
    justify-items: start;
  }
}
</style>
