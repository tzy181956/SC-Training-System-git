<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{
  assignment?: any | null
  session?: any | null
  athleteName?: string | null
  activeItemId?: number | null
  onSelectItem?: ((itemId: number) => void) | null
}>()

const items = computed(() => props.session?.items || props.assignment?.template?.items || [])
const itemListRef = ref<HTMLElement | null>(null)

async function scrollActiveItemIntoView() {
  if (!props.session || !props.activeItemId) return
  await nextTick()
  const activeElement = itemListRef.value?.querySelector<HTMLElement>(`[data-item-id="${props.activeItemId}"]`)
  activeElement?.scrollIntoView({ block: 'nearest' })
}

watch(
  () => [props.activeItemId, items.value.length],
  () => {
    void scrollActiveItemIntoView()
  },
  { immediate: true },
)
</script>

<template>
  <section class="panel overview">
    <div v-if="session || assignment" class="heading">
      <div class="heading-copy">
        <p class="section-title">4. 查看计划</p>
        <h3>{{ assignment?.template?.name || '未选择计划' }}</h3>
        <p class="current-athlete">当前队员：{{ athleteName || '未选择队员' }}</p>
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

    <div v-if="items.length" ref="itemListRef" class="item-list">
      <button
        v-for="item in items"
        :key="item.id"
        :data-item-id="item.id"
        class="item-card"
        :class="{ active: session && item.id === activeItemId }"
        @click="session && onSelectItem && onSelectItem(item.id)"
      >
        <strong>{{ item.exercise.name }}</strong>
        <span>{{ item.prescribed_sets }} 组 × {{ item.prescribed_reps }} 次</span>
        <span>{{ item.target_note || '按设定目标完成本动作' }}</span>
        <em v-if="session">{{ item.records.length }}/{{ item.prescribed_sets }} 已完成</em>
      </button>
    </div>
  </section>
</template>

<style scoped>
.overview,.heading,.item-list,.empty-state{display:grid;gap:12px}.overview{gap:16px;grid-template-rows:auto minmax(0,1fr);min-height:0}
.heading-copy{display:grid;gap:8px}
.heading h3,.section-title,.meta span,.item-card span,.empty-state span{margin:0;color:var(--muted)}
.current-athlete{margin:0;display:inline-flex;align-items:center;width:fit-content;padding:6px 10px;border-radius:999px;background:var(--panel-soft);color:var(--text);font-size:13px;line-height:1.2;font-weight:700}
.item-list{min-height:0;overflow-y:auto;padding-right:6px;scrollbar-gutter:stable;align-content:start}
.item-card{background:var(--panel-soft);border-radius:18px;padding:16px;display:grid;gap:6px;text-align:left}
.item-card.active{background:#dbeafe}
.item-card em{font-style:normal;color:var(--primary);font-weight:700}
</style>
