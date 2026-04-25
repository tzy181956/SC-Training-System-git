<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const innerWidth = ref(0)
const innerHeight = ref(0)
const devicePixelRatioValue = ref(1)
let visualViewport: VisualViewport | null = null

const layoutMode = computed(() => {
  if (innerWidth.value < 768) return 'mobile'
  if (innerWidth.value < 1200) return 'tablet'
  return 'desktop'
})

function syncViewport() {
  innerWidth.value = window.innerWidth
  innerHeight.value = window.innerHeight
  devicePixelRatioValue.value = window.devicePixelRatio || 1
}

function handleResize() {
  syncViewport()
}

onMounted(() => {
  syncViewport()
  window.addEventListener('resize', handleResize)
  visualViewport = window.visualViewport || null
  visualViewport?.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  visualViewport?.removeEventListener('resize', handleResize)
})
</script>

<template>
  <aside class="debug-card">
    <strong class="debug-title">Training Layout Debug</strong>
    <div class="debug-grid">
      <span>width</span>
      <strong>{{ innerWidth }}</strong>
      <span>height</span>
      <strong>{{ innerHeight }}</strong>
      <span>dpr</span>
      <strong>{{ devicePixelRatioValue.toFixed(2) }}</strong>
      <span>mode</span>
      <strong>{{ layoutMode }}</strong>
    </div>
  </aside>
</template>

<style scoped>
.debug-card {
  position: fixed;
  right: 14px;
  bottom: 14px;
  z-index: 90;
  display: grid;
  gap: 8px;
  min-width: 188px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 118, 110, 0.2);
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.84);
  color: #f8fafc;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(8px);
  pointer-events: none;
}

.debug-title,
.debug-grid strong,
.debug-grid span {
  font-family: Consolas, 'SFMono-Regular', Monaco, monospace;
}

.debug-title {
  font-size: 12px;
  line-height: 1.2;
  letter-spacing: 0.02em;
}

.debug-grid {
  display: grid;
  grid-template-columns: auto auto;
  gap: 4px 12px;
  align-items: center;
}

.debug-grid span {
  font-size: 12px;
  line-height: 1.2;
  opacity: 0.76;
}

.debug-grid strong {
  font-size: 12px;
  line-height: 1.2;
  text-align: right;
}
 </style>
