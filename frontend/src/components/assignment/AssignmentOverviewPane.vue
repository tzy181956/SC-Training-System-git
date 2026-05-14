<script setup lang="ts">
import { computed } from 'vue'

import { formatRepeatWeekdays } from '@/constants/repeatWeekdays'

const props = defineProps<{
  overview: any
  groups: any[]
  unassignedAthletes: any[]
  selectedGroupKey: string | null
  selectedAssignmentsByGroupKey: Record<string, number[]>
  confirmDeleteGroupKey: string | null
  targetDate: string
  cancelling?: boolean
}>()

const emit = defineEmits<{
  selectGroup: [groupKey: string]
  switchToBuilder: []
  toggleAssignment: [groupKey: string, assignmentId: number]
  requestCancel: [groupKey: string]
  resetCancel: []
  confirmCancel: [groupKey: string]
}>()

const selectedGroup = computed(() =>
  props.groups.find((group) => groupKey(group) === props.selectedGroupKey) || null,
)

const selectedGroupAssignmentIds = computed(() => {
  if (!selectedGroup.value) return []
  return props.selectedAssignmentsByGroupKey[groupKey(selectedGroup.value)] ?? []
})

function groupKey(group: any) {
  return group.assignment_ids.join('-')
}

function athletePreview(group: any) {
  const names = (group.athletes || []).slice(0, 4).map((athlete: any) => athlete.full_name)
  const remaining = Math.max((group.athletes?.length || 0) - names.length, 0)
  return remaining ? `${names.join('、')} +${remaining} 人` : names.join('、')
}

function groupNotesPreview(group: any) {
  return (group.notes || []).slice(0, 2).join('；')
}

function isGroupSelected(group: any) {
  return groupKey(group) === props.selectedGroupKey
}

function isAssignmentSelected(group: any, assignmentId: number) {
  return (props.selectedAssignmentsByGroupKey[groupKey(group)] ?? []).includes(assignmentId)
}

function selectedCount(group: any) {
  return (props.selectedAssignmentsByGroupKey[groupKey(group)] ?? []).length
}
</script>

<template>
  <section class="overview-shell">
    <div class="summary-grid">
      <article class="summary-card">
        <span class="summary-label">已安排队员</span>
        <strong>{{ overview.assigned_count }}</strong>
        <small>按当前查看日期向后统计</small>
      </article>
      <article class="summary-card">
        <span class="summary-label">有效计划组</span>
        <strong>{{ overview.group_count }}</strong>
        <small>按模板、时间段和执行日归并</small>
      </article>
      <article class="summary-card summary-card--subtle">
        <span class="summary-label">未分配队员</span>
        <strong>{{ overview.unassigned_count }}</strong>
        <small>可切到新建分配直接补齐</small>
      </article>
    </div>

    <div class="overview-grid">
      <section class="panel pane-card list-card">
        <div class="pane-head">
          <div>
            <p class="eyebrow">现有分配</p>
            <h3>查看 {{ targetDate }} 起已安排的计划</h3>
          </div>
          <span class="muted">共 {{ groups.length }} 组</span>
        </div>

        <div v-if="groups.length" class="group-list">
          <button
            v-for="group in groups"
            :key="groupKey(group)"
            class="group-card"
            :class="{ active: isGroupSelected(group) }"
            type="button"
            @click="emit('selectGroup', groupKey(group))"
          >
            <div class="group-head">
              <div>
                <strong>{{ group.template.name }}</strong>
                <p>{{ group.start_date }} 至 {{ group.end_date }}</p>
                <p>{{ formatRepeatWeekdays(group.repeat_weekdays) }}</p>
              </div>
              <div class="group-badges">
                <span class="status-badge" :class="group.group_status === 'active_now' ? 'status-badge--active' : 'status-badge--upcoming'">
                  {{ group.group_status === 'active_now' ? '进行中' : '即将开始' }}
                </span>
                <span class="badge">{{ group.athlete_count }} 人</span>
              </div>
            </div>
            <p class="group-preview">{{ athletePreview(group) }}</p>
            <p v-if="group.notes?.length" class="group-notes">备注：{{ groupNotesPreview(group) }}</p>
          </button>
        </div>

        <div v-else class="overview-empty">
          <strong>当前筛选条件下没有有效计划组</strong>
          <p class="muted">可在新建分配中为队员安排模板和执行周期。</p>
          <button class="primary-btn" type="button" @click="emit('switchToBuilder')">去新建分配</button>
        </div>
      </section>

      <section class="panel pane-card detail-card">
        <template v-if="selectedGroup">
          <div class="pane-head">
            <div>
              <p class="eyebrow">计划组详情</p>
              <h3>{{ selectedGroup.template.name }}</h3>
            </div>
            <span class="muted">已选 {{ selectedGroupAssignmentIds.length }} 人</span>
          </div>

          <div class="detail-meta">
            <div>
              <strong>时间段</strong>
              <span>{{ selectedGroup.start_date }} 至 {{ selectedGroup.end_date }}</span>
            </div>
            <div>
              <strong>执行日</strong>
              <span>{{ formatRepeatWeekdays(selectedGroup.repeat_weekdays) }}</span>
            </div>
            <div>
              <strong>计划状态</strong>
              <span>{{ selectedGroup.group_status === 'active_now' ? '进行中' : '即将开始' }}</span>
            </div>
          </div>

          <div v-if="selectedGroup.notes?.length" class="info-box">
            <strong>备注摘要</strong>
            <span>{{ selectedGroup.notes.join('；') }}</span>
          </div>

          <div class="detail-section">
            <div class="detail-section-head">
              <div>
                <p class="eyebrow">完整名单</p>
                <h4>{{ selectedGroup.athlete_count }} 人</h4>
              </div>
            </div>
            <div class="athlete-list">
              <button
                v-for="entry in selectedGroup.entries"
                :key="entry.assignment_id"
                class="athlete-row"
                :class="{ active: isAssignmentSelected(selectedGroup, entry.assignment_id) }"
                type="button"
                @click="emit('toggleAssignment', groupKey(selectedGroup), entry.assignment_id)"
              >
                <div>
                  <strong>{{ entry.athlete.full_name }}</strong>
                  <span>{{ entry.athlete.team?.name || '未分队' }}</span>
                </div>
                <small>{{ entry.notes || '无分配备注' }}</small>
              </button>
            </div>
          </div>

          <div class="danger-box">
            <div>
              <strong>取消分配</strong>
              <p class="muted">只对右侧已选中的队员执行取消，不影响同组其他人的计划。</p>
            </div>
            <div class="danger-actions">
              <template v-if="confirmDeleteGroupKey === groupKey(selectedGroup)">
                <span class="warning-text">确认取消当前所选 {{ selectedCount(selectedGroup) }} 人的计划？</span>
                <button class="ghost-btn slim" type="button" :disabled="cancelling" @click="emit('resetCancel')">取消</button>
                <button class="ghost-btn slim danger-btn" type="button" :disabled="cancelling" @click="emit('confirmCancel', groupKey(selectedGroup))">
                  {{ cancelling ? '取消中...' : '确认取消' }}
                </button>
              </template>
              <button
                v-else
                class="ghost-btn slim danger-btn"
                type="button"
                :disabled="!selectedCount(selectedGroup) || cancelling"
                @click="emit('requestCancel', groupKey(selectedGroup))"
              >
                取消所选分配
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="pane-head">
            <div>
              <p class="eyebrow">未分配摘要</p>
              <h3>选择计划组查看详情</h3>
            </div>
            <span class="muted">当前还有 {{ unassignedAthletes.length }} 人未分配</span>
          </div>

          <div class="detail-section">
            <div class="detail-section-head">
              <div>
                <p class="eyebrow">待补齐对象</p>
                <h4>未分配队员</h4>
              </div>
            </div>
            <div class="athlete-list athlete-list--readonly">
              <div v-for="athlete in unassignedAthletes.slice(0, 8)" :key="athlete.id" class="athlete-row athlete-row--static">
                <div>
                  <strong>{{ athlete.full_name }}</strong>
                  <span>{{ athlete.team?.name || '未分队' }}</span>
                </div>
              </div>
            </div>
          </div>

          <button class="primary-btn" type="button" @click="emit('switchToBuilder')">去新建分配</button>
        </template>
      </section>
    </div>
  </section>
</template>

<style scoped>
.overview-shell,
.summary-grid,
.overview-grid,
.group-list,
.detail-meta,
.detail-section,
.athlete-list {
  display: grid;
  gap: 16px;
}

.overview-shell {
  gap: 18px;
}

.summary-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.overview-grid {
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr);
  align-items: start;
}

.pane-card,
.summary-card,
.group-card,
.athlete-row,
.info-box,
.danger-box {
  display: grid;
  gap: 10px;
}

.pane-card {
  padding: 18px;
  align-content: start;
}

.summary-card {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.summary-card--subtle {
  background: rgba(241, 245, 249, 0.8);
}

.summary-card strong {
  font-size: 32px;
}

.summary-label,
.eyebrow,
.muted,
.group-card p,
.athlete-row span,
.athlete-row small,
.summary-card small,
.warning-text,
.info-box span,
.detail-meta span {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.pane-head,
.group-head,
.group-badges,
.detail-section-head,
.danger-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.group-list {
  gap: 12px;
}

.group-card {
  width: 100%;
  text-align: left;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.78);
  color: inherit;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}

.group-card:hover,
.group-card.active {
  border-color: rgba(15, 118, 110, 0.22);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
}

.group-card.active {
  background: rgba(240, 253, 250, 0.9);
}

.group-preview {
  font-weight: 600;
  color: var(--text);
}

.group-notes {
  color: var(--text-soft);
}

.badge,
.status-badge {
  min-width: 72px;
  padding: 8px 12px;
  border-radius: 999px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
}

.badge {
  background: rgba(15, 118, 110, 0.12);
  color: var(--primary);
}

.status-badge--active {
  background: rgba(15, 118, 110, 0.16);
  color: var(--primary);
}

.status-badge--upcoming {
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
}

.detail-card {
  position: sticky;
  top: 18px;
}

.detail-meta {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-meta > div,
.info-box,
.danger-box {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.74);
}

.info-box {
  background: rgba(240, 253, 250, 0.86);
}

.athlete-list {
  gap: 10px;
}

.athlete-row {
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.76);
  color: inherit;
  cursor: pointer;
}

.athlete-row.active {
  border-color: rgba(185, 28, 28, 0.18);
  background: rgba(254, 242, 242, 0.9);
}

.athlete-row--static {
  cursor: default;
}

.athlete-row strong,
.detail-meta strong,
.info-box strong,
.danger-box strong {
  display: block;
}

.danger-box {
  border: 1px solid rgba(185, 28, 28, 0.14);
  background: rgba(254, 242, 242, 0.9);
}

.warning-text {
  color: #b91c1c;
}

.overview-empty {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(241, 245, 249, 0.76);
}

@media (max-width: 1280px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .detail-card {
    position: static;
  }
}

@media (max-width: 900px) {
  .summary-grid,
  .detail-meta {
    grid-template-columns: 1fr;
  }
}
</style>
