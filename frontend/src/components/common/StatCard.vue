<script setup lang="ts">
defineProps<{ label: string; value: string | number; hint?: string }>()
</script>

<template>
  <div class="stat-card">
    <p>{{ label }}</p>
    <strong>{{ value }}</strong>
    <span>{{ hint }}</span>
  </div>
</template>

<style scoped>
.stat-card { background: var(--panel); border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); display: grid; gap: 8px; }
p, span { margin: 0; color: var(--muted); }
strong { font-size: 28px; }
</style>
