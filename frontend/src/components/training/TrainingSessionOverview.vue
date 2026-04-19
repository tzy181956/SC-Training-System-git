<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  assignment?: any | null
  session?: any | null
  activeItemId?: number | null
  onSelectItem?: ((itemId: number) => void) | null
}>()

const items = computed(() => props.session?.items || props.assignment?.template?.items || [])
</script>

<template>
  <section class="panel overview">
    <div v-if="session || assignment" class="heading">
      <div>
        <p class="section-title">4. 查看计划</p>
        <h3>{{ assignment?.template?.name || '未选择计划' }}</h3>
      </div>
      <div class="meta">
        <span>{{ items.length }} 个动作</span>
        <span>{{ assignment?.notes || session?.coach_note || '按动作顺序完成即可' }}</span>
      </div>
    </div>

    <div v-else class="empty-state">
      <strong>先选择日期，再选择队员。</strong>
      <span>如果该队员当天有多份计划，会直接显示在队员名字下方供点击选择。</span>
    </div>

    <div v-if="items.length" class="item-list">
      <button
        v-for="item in items"
        :key="item.id"
        class="item-card"
        :class="{ active: session && item.id === activeItemId }"
        @click="session && onSelectItem && onSelectItem(item.id)"
      >
        <strong>{{ item.sort_order }}. {{ item.exercise.name }}</strong>
        <span>{{ item.prescribed_sets }} 组 × {{ item.prescribed_reps }} 次</span>
        <span>{{ item.target_note || '按设定目标完成本动作' }}</span>
        <em v-if="session">{{ item.records.length }}/{{ item.prescribed_sets }} 已完成</em>
      </button>
    </div>
  </section>
</template>

<style scoped>
.overview,.heading,.item-list,.empty-state{display:grid;gap:12px}.overview{gap:16px;align-content:start}
.heading h3,.section-title,.meta span,.item-card span,.empty-state span{margin:0;color:var(--muted)}
.item-card{background:var(--panel-soft);border-radius:18px;padding:16px;display:grid;gap:6px;text-align:left}
.item-card.active{background:#dbeafe}
.item-card em{font-style:normal;color:var(--primary);font-weight:700}
</style>
