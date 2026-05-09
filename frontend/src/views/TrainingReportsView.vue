<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { fetchAthletes } from '@/api/athletes'
import { retryTrainingSyncIssue } from '@/api/sessions'
import { fetchTrainingReport, type TrainingReportResponse } from '@/api/trainingReports'
import StatCard from '@/components/common/StatCard.vue'
import AppShell from '@/components/layout/AppShell.vue'
import TrainingSessionCard from '@/components/report/TrainingSessionCard.vue'
import { getTrainingSyncIssueLabel, isTrainingSyncConflictSummary } from '@/constants/trainingSync'
import { getTrainingStatusLabel } from '@/constants/trainingStatus'
import { todayString } from '@/utils/date'

const route = useRoute()
const athletes = ref<any[]>([])
const loading = ref(false)
const report = ref<TrainingReportResponse | null>(null)
const reportNotice = ref('')
const reportNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const retryingIssueId = ref<number | null>(null)
const mainLiftChartRef = ref<HTMLDivElement | null>(null)
const completionChartRef = ref<HTMLDivElement | null>(null)
let mainLiftChart: echarts.ECharts | null = null
let completionChart: echarts.ECharts | null = null
const completedStatusLabel = getTrainingStatusLabel('completed')

const filters = reactive({
  athleteId: parseNumberQuery(route.query.athleteId),
  dateFrom: parseStringQuery(route.query.dateFrom) || getDateBefore(29),
  dateTo: parseStringQuery(route.query.dateTo) || todayString(),
  onlyIncomplete: false,
  onlyMainLift: false,
})

async function hydrate() {
  athletes.value = await fetchAthletes()
  if (!filters.athleteId && athletes.value[0]) {
    filters.athleteId = athletes.value[0].id
  }
  if (filters.athleteId) {
    await loadReport()
  }
}

async function loadReport() {
  if (!filters.athleteId) return
  loading.value = true
  try {
    report.value = await fetchTrainingReport({
      athlete_id: filters.athleteId,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
    })
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

async function retrySyncIssue(issueId: number) {
  retryingIssueId.value = issueId
  try {
    await retryTrainingSyncIssue(issueId)
    reportNotice.value = '同步异常已重试，待处理标记已刷新。'
    reportNoticeTone.value = 'success'
    await loadReport()
  } catch {
    reportNotice.value = '手动重试失败，请回到训练模式所在设备继续处理。'
    reportNoticeTone.value = 'warning'
  } finally {
    retryingIssueId.value = null
  }
}

function showNotice(payload: { message: string; tone: 'success' | 'warning' | 'error' }) {
  reportNotice.value = payload.message
  reportNoticeTone.value = payload.tone
}

function renderCharts() {
  if (mainLiftChartRef.value && report.value) {
    mainLiftChart ||= echarts.init(mainLiftChartRef.value)
    mainLiftChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 48, right: 24, top: 42, bottom: 24 },
      xAxis: { type: 'category' },
      yAxis: { type: 'value', name: '重量（公斤）' },
      series: (report.value.trend.main_lift_series || []).map((item: any) => ({
        name: item.exercise_name,
        type: 'line',
        smooth: true,
        data: item.points.map((point: any) => [point.session_date, point.value]),
      })),
    })
  }

  if (completionChartRef.value && report.value) {
    completionChart ||= echarts.init(completionChartRef.value)
    const points = report.value.trend.completion_series || []
    completionChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 24, top: 24, bottom: 24 },
      xAxis: { type: 'category', data: points.map((item: any) => item.session_date) },
      yAxis: { type: 'value', name: '完成率（%）', max: 100 },
      series: [
        {
          name: '完成率',
          type: 'bar',
          data: points.map((item: any) => item.completion_rate),
          itemStyle: { color: '#0f766e' },
        },
      ],
    })
  }
}

watch(
  () => [filters.athleteId, filters.dateFrom, filters.dateTo],
  () => {
    if (filters.athleteId) {
      loadReport()
    }
  },
)

onMounted(hydrate)

function getDateBefore(days: number) {
  const current = new Date()
  current.setDate(current.getDate() - days)
  const year = current.getFullYear()
  const month = String(current.getMonth() + 1).padStart(2, '0')
  const day = String(current.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseNumberQuery(value: unknown) {
  if (typeof value !== 'string') return 0
  const parsed = Number(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

function parseStringQuery(value: unknown) {
  return typeof value === 'string' ? value : ''
}
</script>

<template>
  <AppShell>
    <div class="report-layout">
      <aside class="panel filter-panel">
        <div>
          <p class="eyebrow">筛选条件</p>
          <h3>训练数据</h3>
        </div>

        <label class="field">
          <span>运动员</span>
          <select v-model.number="filters.athleteId" class="text-input">
            <option v-for="athlete in athletes" :key="athlete.id" :value="athlete.id">
              {{ athlete.full_name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>开始日期</span>
          <input v-model="filters.dateFrom" type="date" class="text-input" />
        </label>

        <label class="field">
          <span>结束日期</span>
          <input v-model="filters.dateTo" type="date" class="text-input" />
        </label>

        <label class="checkbox-row">
          <input v-model="filters.onlyIncomplete" type="checkbox" />
          <span>仅看未完成训练</span>
        </label>

        <label class="checkbox-row">
          <input v-model="filters.onlyMainLift" type="checkbox" />
          <span>仅看主项动作</span>
        </label>

        <button class="primary-btn" @click="loadReport">刷新数据</button>
      </aside>

      <section class="report-main">
        <template v-if="report">
          <div class="summary-grid">
            <StatCard label="训练课次" :value="report.summary.total_sessions" hint="当前时间范围内的训练课次数" />
            <StatCard label="已完成课次" :value="report.summary.completed_sessions" :hint="`状态为${completedStatusLabel}的训练课次`" />
            <StatCard
              label="已完成组数"
              :value="`${report.summary.completed_sets}/${report.summary.total_sets}`"
              hint="已完成组数 / 目标组数"
            />
            <StatCard
              label="完成率"
              :value="`${report.summary.completion_rate}%`"
              :hint="report.summary.latest_session_date ? `最近训练：${report.summary.latest_session_date}` : '当前暂无训练记录'"
            />
          </div>

          <p v-if="reportNotice" class="report-notice" :class="reportNoticeTone">{{ reportNotice }}</p>

          <section class="panel sync-issue-panel">
            <div class="panel-head">
              <div>
                <p class="eyebrow">同步</p>
                <h3>同步异常待处理</h3>
              </div>
            </div>
            <div v-if="report.sync_issues?.length" class="sync-issue-list">
              <article v-for="issue in report.sync_issues" :key="issue.id" class="sync-issue-card">
                <div class="sync-issue-copy">
                  <strong>{{ issue.session_date }} {{ getTrainingSyncIssueLabel(issue.summary) }}</strong>
                  <p class="sync-issue-tag" :class="{ conflict: isTrainingSyncConflictSummary(issue.summary) }">
                    {{ getTrainingSyncIssueLabel(issue.summary) }}
                  </p>
                  <p>{{ issue.summary }}</p>
                  <p v-if="issue.last_error" class="sync-issue-error">最近错误：{{ issue.last_error }}</p>
                </div>
                <button
                  class="secondary-btn"
                  type="button"
                  :disabled="retryingIssueId === issue.id"
                  @click="retrySyncIssue(issue.id)"
                >
                  {{ retryingIssueId === issue.id ? '重试中...' : '手动重试' }}
                </button>
              </article>
            </div>
            <div v-else class="empty-state">当前筛选范围内没有待处理的同步异常。</div>
          </section>

          <div class="two-col-panels">
            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">趋势</p>
                  <h3>主项最终重量趋势</h3>
                </div>
              </div>
              <div v-if="report.trend.main_lift_series.length" ref="mainLiftChartRef" class="chart"></div>
              <div v-else class="empty-state">当前时间范围内暂无主项趋势数据。</div>
            </section>

            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">趋势</p>
                  <h3>课次完成度趋势</h3>
                </div>
              </div>
              <div v-if="report.trend.completion_series.length" ref="completionChartRef" class="chart"></div>
              <div v-else class="empty-state">当前时间范围内暂无完成度趋势数据。</div>
            </section>
          </div>

          <section class="panel flag-panel">
            <div class="panel-head">
              <div>
                <p class="eyebrow">提醒</p>
                <h3>训练异常提示</h3>
              </div>
            </div>
            <div v-if="report.flags.length" class="flag-grid">
              <article v-for="(flag, index) in report.flags" :key="index" class="flag-card">
                <strong>{{ flag.level }}：{{ flag.title }}</strong>
                <p>{{ flag.description }}</p>
              </article>
            </div>
            <div v-else class="empty-state">当前时间范围内暂无异常提示。</div>
          </section>

          <section class="panel session-panel">
            <div class="panel-head">
              <div>
                <p class="eyebrow">明细</p>
                <h3>训练课次记录</h3>
              </div>
            </div>

            <div v-if="report.sessions.length" class="session-list">
              <TrainingSessionCard
                v-for="session in report.sessions"
                :key="session.id"
                :session="session"
                :only-incomplete="filters.onlyIncomplete"
                :only-main-lift="filters.onlyMainLift"
                @changed="loadReport"
                @notify="showNotice"
              />
            </div>
            <div v-else class="empty-state">当前时间范围内暂无训练记录。</div>
          </section>
        </template>

        <section v-else class="panel empty-panel">
          <h3>请选择运动员查看训练数据</h3>
          <p>{{ loading ? '正在加载训练数据，请稍候。' : '左侧选择运动员和时间范围后，即可查看训练执行情况、趋势和异常提醒。' }}</p>
        </section>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.report-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  min-width: 0;
}

.filter-panel,
.report-main,
.flag-grid,
.session-list {
  display: grid;
  gap: 14px;
  align-content: start;
}

.report-main {
  min-width: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.report-notice {
  margin: 0;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
}

.report-notice.success {
  background: #dcfce7;
  color: #166534;
}

.report-notice.warning {
  background: #fef3c7;
  color: #92400e;
}

.report-notice.error {
  background: #fee2e2;
  color: #b91c1c;
}

.two-col-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.sync-issue-list {
  display: grid;
  gap: 12px;
}

.sync-issue-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(245, 158, 11, 0.28);
  background: rgba(245, 158, 11, 0.1);
}

.sync-issue-copy {
  display: grid;
  gap: 6px;
}

.sync-issue-tag {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.14);
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
}

.sync-issue-tag.conflict {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.sync-issue-copy strong,
.sync-issue-copy p,
.sync-issue-error {
  margin: 0;
}

.sync-issue-error {
  color: #92400e;
  font-size: 13px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.eyebrow,
.field span,
.flag-card p,
.empty-state {
  margin: 0;
  color: var(--text-soft);
  font-size: 14px;
}

.field {
  display: grid;
  gap: 8px;
}

.checkbox-row {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: var(--touch);
}

.chart {
  width: 100%;
  height: 300px;
}

.flag-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.flag-card {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.24);
  border-radius: 18px;
  padding: 16px;
}

.empty-panel,
.empty-state {
  padding: 20px;
}

@media (max-width: 1280px) {
  .report-layout,
  .summary-grid,
  .two-col-panels,
  .flag-grid {
    grid-template-columns: 1fr;
  }
}
</style>
