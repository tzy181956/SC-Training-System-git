<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'

import type { RuntimeAccessInfo } from '@/api/runtimeAccess'

const props = defineProps<{
  info: RuntimeAccessInfo
}>()

const copied = ref(false)
const qrDataUrl = ref('')
const panelOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const accessHint = computed(() =>
  props.info.source === 'fallback' ? '当前访问地址（兜底显示）' : '同一网络下可直接访问',
)
const triggerLabel = computed(() => (props.info.source === 'fallback' ? '当前地址' : '训练入口'))

async function buildQrCode() {
  qrDataUrl.value = await QRCode.toDataURL(props.info.accessUrl, {
    errorCorrectionLevel: 'M',
    margin: 1,
    width: 112,
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

function togglePanel() {
  panelOpen.value = !panelOpen.value
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!rootRef.value?.contains(event.target as Node)) {
    panelOpen.value = false
  }
}

function handleEscapeKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    panelOpen.value = false
  }
}

watch(
  () => props.info.accessUrl,
  () => {
    buildQrCode()
  },
  { immediate: true },
)

onMounted(() => {
  buildQrCode()
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  document.addEventListener('keydown', handleEscapeKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  document.removeEventListener('keydown', handleEscapeKey)
})
</script>

<template>
  <div ref="rootRef" class="access-card">
    <button
      class="access-trigger"
      type="button"
      :aria-expanded="panelOpen ? 'true' : 'false'"
      aria-haspopup="dialog"
      @click="togglePanel"
    >
      <span class="trigger-dot" :class="props.info.source" />
      <span class="trigger-text">{{ triggerLabel }}</span>
      <span class="trigger-chevron">{{ panelOpen ? '▴' : '▾' }}</span>
    </button>

    <div v-if="panelOpen" class="access-panel" role="dialog" aria-label="训练模式访问入口">
      <div class="access-copy">
        <div class="access-heading">
          <p class="eyebrow">{{ accessHint }}</p>
          <small v-if="info.generatedAt" class="access-meta">生成时间：{{ info.generatedAt }}</small>
        </div>
        <a class="access-link" :href="info.accessUrl" target="_blank" rel="noreferrer">{{ info.accessUrl }}</a>
        <div class="access-actions">
          <button class="ghost-btn slim" type="button" @click="copyUrl">{{ copied ? '已复制' : '复制地址' }}</button>
          <button class="ghost-btn slim" type="button" @click="panelOpen = false">收起</button>
        </div>
      </div>

      <div class="qr-panel">
        <img v-if="qrDataUrl" :src="qrDataUrl" alt="训练模式访问二维码" class="qr-image" />
        <span>扫码进入</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.access-card {
  position: relative;
  display: flex;
  justify-content: flex-start;
  min-width: 0;
}

.access-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: var(--panel-soft);
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 700;
  white-space: nowrap;
}

.trigger-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex-shrink: 0;
  background: #0f766e;
}

.trigger-dot.fallback {
  background: #64748b;
}

.trigger-text,
.trigger-chevron {
  line-height: 1;
}

.trigger-chevron {
  color: var(--muted);
}

.access-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 30;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  width: min(360px, calc(100vw - 32px));
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(10px);
}

.access-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.access-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  flex-wrap: wrap;
}

.eyebrow {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--text);
}

.access-meta,
.qr-panel {
  color: var(--muted);
}

.access-link {
  color: var(--primary);
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.2;
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
  align-content: start;
  gap: 6px;
  text-align: center;
}

.qr-image {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  background: white;
  padding: 5px;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

@media (min-width: 768px) and (max-width: 1199px) {
  .access-trigger {
    min-height: 38px;
    padding: 0 10px;
    font-size: 0.84rem;
  }

  .access-panel {
    width: min(320px, calc(100vw - 32px));
    gap: 10px;
    padding: 12px;
    border-radius: 16px;
  }

  .access-link {
    font-size: 0.84rem;
  }

  .access-meta {
    font-size: 11px;
  }

  .qr-image {
    width: 64px;
    height: 64px;
  }

  .qr-panel {
    font-size: 11px;
  }
}

@media (max-width: 767px) {
  .access-panel {
    left: 0;
    right: auto;
    grid-template-columns: 1fr;
  }

  .qr-panel {
    justify-items: start;
    text-align: left;
  }
}
</style>
