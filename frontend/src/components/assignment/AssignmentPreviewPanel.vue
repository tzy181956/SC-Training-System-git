<script setup lang="ts">
defineProps<{
  preview: any | null
}>()
</script>

<template>
  <section class="panel preview-panel">
    <div class="section-head">
      <div>
        <p class="eyebrow">第四步</p>
        <h3>分配预览</h3>
      </div>
      <div v-if="preview" class="meta">
        <span>{{ preview.start_date }} 至 {{ preview.end_date }}</span>
        <strong>{{ preview.template.name }}</strong>
      </div>
    </div>

    <div v-if="!preview" class="empty-state">
      <h4>请先完成前面的选择</h4>
      <p>选择运动员、模板和周期后，将在这里展示批量分配的详细预览。</p>
    </div>

    <div v-else class="preview-body">
      <article v-for="row in preview.rows" :key="row.athlete.id" class="preview-card">
        <header class="card-head">
          <div>
            <strong>{{ row.athlete.full_name }}</strong>
            <span>{{ row.athlete.team?.name || '未分组' }} / {{ row.athlete.position || '未填写位置' }}</span>
          </div>
        </header>
        <div class="item-grid">
          <div
            v-for="item in row.items"
            :key="`${row.athlete.id}-${item.template_item_id}`"
            class="item-row"
            :class="{ warning: item.status === 'missing_basis' }"
          >
            <div>
              <strong>{{ item.exercise_name }}</strong>
              <p>{{ item.load_mode_label }}</p>
            </div>
            <div class="item-side">
              <span>{{ item.computed_load ?? '--' }} <template v-if="item.computed_load !== null">公斤</template></span>
              <small>{{ item.basis_label || (item.status === 'missing_basis' ? '缺少测试基准' : '可分配') }}</small>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.preview-panel,
.preview-body,
.preview-card,
.item-grid {
  display: grid;
  gap: 14px;
}

.section-head,
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.eyebrow,
.meta span,
.card-head span,
.item-row p,
.item-side small {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.meta,
.item-side {
  display: grid;
  gap: 4px;
  text-align: right;
}

.preview-card {
  padding: 16px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.item-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
}

.item-row.warning {
  border: 1px solid rgba(220, 38, 38, 0.22);
  background: rgba(254, 226, 226, 0.7);
}

.empty-state {
  padding: 28px;
  border-radius: 18px;
  background: var(--panel-soft);
}
</style>
