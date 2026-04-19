<script setup lang="ts">
defineProps<{
  session: any
  onlyIncomplete?: boolean
  onlyMainLift?: boolean
}>()

function adjustmentClass(type: string) {
  if (type === '按建议执行') return 'accepted'
  if (type === '按建议调整') return 'guided'
  return 'modified'
}
</script>

<template>
  <details class="session-card">
    <summary class="session-head">
      <div class="session-copy adaptive-card">
        <p class="session-date">{{ session.session_date }}</p>
        <h4 class="adaptive-card-title">{{ session.template_name }}</h4>
      </div>
      <div class="session-meta">
        <span class="status-chip">{{ session.status }}</span>
        <span>{{ session.completed_items }}/{{ session.total_items }} 个动作</span>
        <span>{{ session.completed_sets }}/{{ session.total_sets }} 组</span>
      </div>
    </summary>

    <div class="session-body">
      <article
        v-for="item in session.items"
        :key="item.id"
        v-show="(!onlyIncomplete || item.status !== 'completed') && (!onlyMainLift || item.is_main_lift)"
        class="item-card"
      >
        <div class="item-head">
          <div class="item-copy adaptive-card">
            <h5 class="adaptive-card-title">{{ item.exercise_name }}</h5>
            <p class="adaptive-card-subtitle adaptive-card-clamp-2">
              {{ item.completed_sets }}/{{ item.prescribed_sets }} 组，目标 {{ item.prescribed_reps }} 次
            </p>
          </div>
          <span class="item-badge" :class="{ main: item.is_main_lift }">
            {{ item.is_main_lift ? '主项动作' : '常规动作' }}
          </span>
        </div>

        <p v-if="item.target_note" class="item-note adaptive-card-subtitle adaptive-card-clamp-2">{{ item.target_note }}</p>

        <div class="record-table-wrap">
          <table class="record-table">
            <thead>
              <tr>
                <th>组次</th>
                <th>目标重量</th>
                <th>实际重量</th>
                <th>次数</th>
                <th>RIR</th>
                <th>建议重量</th>
                <th>最终采用</th>
                <th>调整说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in item.records" :key="record.id">
                <td>第 {{ record.set_number }} 组</td>
                <td>{{ record.target_weight ?? '-' }}</td>
                <td>{{ record.actual_weight }}</td>
                <td>{{ record.actual_reps }}</td>
                <td>{{ record.actual_rir }}</td>
                <td>{{ record.suggestion_weight ?? '-' }}</td>
                <td>{{ record.final_weight }}</td>
                <td>
                  <span class="decision-pill" :class="adjustmentClass(record.adjustment_type)">
                    {{ record.adjustment_type }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>
  </details>
</template>

<style scoped>
.session-card {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: white;
  overflow: hidden;
}

.session-head {
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 20px;
  cursor: pointer;
}

.session-head::-webkit-details-marker {
  display: none;
}

.session-copy,
.item-copy {
  min-width: 0;
  flex: 1;
}

.session-date,
.item-head p,
.item-note {
  margin: 0;
  color: var(--text-soft);
}

.session-head h4,
.item-head h5 {
  margin: 4px 0 0;
}

.session-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  color: var(--text-soft);
  font-size: 14px;
}

.status-chip,
.item-badge,
.decision-pill {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
}

.status-chip {
  background: rgba(15, 118, 110, 0.14);
  color: #0f766e;
}

.item-badge {
  background: var(--panel-soft);
  color: var(--text);
  flex-shrink: 0;
}

.item-badge.main {
  background: rgba(251, 191, 36, 0.18);
  color: #92400e;
}

.decision-pill.accepted {
  background: rgba(34, 197, 94, 0.16);
  color: #166534;
}

.decision-pill.guided {
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
}

.decision-pill.modified {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.session-body {
  padding: 0 20px 20px;
  display: grid;
  gap: 14px;
}

.item-card {
  border-radius: 18px;
  background: var(--panel-soft);
  padding: 16px;
  display: grid;
  gap: 12px;
}

.item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.record-table-wrap {
  overflow: auto;
}

.record-table {
  width: 100%;
  border-collapse: collapse;
}

.record-table th,
.record-table td {
  padding: 10px 8px;
  text-align: left;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
</style>
