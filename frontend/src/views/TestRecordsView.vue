<script setup lang="ts">
import axios from 'axios'
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

import { fetchAthletes } from '@/api/athletes'
import {
  createTestRecord,
  deleteTestRecordsBatch,
  downloadTestRecordTemplate,
  exportTestRecordLibrary,
  fetchTestRecords,
  importTestRecords,
} from '@/api/testRecords'
import AppShell from '@/components/layout/AppShell.vue'
import { todayString } from '@/utils/date'
import { confirmDangerousAction } from '@/utils/dangerousAction'

type Athlete = {
  id: number
  full_name: string
  weight?: number | null
  team?: { name?: string | null } | null
}

type TestRecord = {
  id: number
  athlete_id: number
  test_date: string
  test_type: string
  metric_name: string
  result_value: number
  result_text?: string | null
  unit: string
  notes?: string | null
  athlete?: Athlete | null
}

type MetricRangePoint = {
  test_date: string
  average_value: number
  min_value: number
  max_value: number
}

const athletes = ref<Athlete[]>([])
const records = ref<TestRecord[]>([])
const chartRef = ref<HTMLDivElement | null>(null)
const importInputRef = ref<HTMLInputElement | null>(null)
const loading = ref(false)
const importBusy = ref(false)
const exportBusy = ref(false)
const templateBusy = ref(false)
const actionMessage = ref('')

let chart: echarts.ECharts | null = null

const testTypeOptions = ['基础身体', '力量测试', '体能测试', '速度测试', '耐力测试']
const metricOptions = ['卧推', '卧拉', '深蹲', '挺举', '引体向上', '反向跳', '静蹲跳', '直腿跳', '助跑摸高', '原地摸高', '3000m', '17折返']
const unitMap: Record<string, string> = {
  卧推: 'kg',
  卧拉: 'kg',
  深蹲: 'kg',
  挺举: 'kg',
  引体向上: '次',
  反向跳: 'cm',
  静蹲跳: 'cm',
  直腿跳: 'RSI',
  助跑摸高: 'cm',
  原地摸高: 'cm',
  '3000m': 's',
  '17折返': 's',
}
const ratioMetrics = new Set(['卧推', '卧拉', '深蹲', '挺举'])

const form = reactive({
  athlete_id: 0,
  test_date: todayString(),
  test_type: '力量测试',
  metric_name: '卧推',
  result_value: 0,
  result_text: '',
  unit: 'kg',
  notes: '',
})

const libraryFilters = reactive({
  athleteKeyword: '',
  metricKeyword: '',
  testType: '',
})

const selectedAthlete = computed(() => athletes.value.find((item) => item.id === form.athlete_id) || null)

const selectedAthleteRecords = computed(() =>
  records.value.filter((item) => !form.athlete_id || item.athlete_id === form.athlete_id),
)

const selectedMetricRecords = computed(() =>
  selectedAthleteRecords.value
    .filter((item) => item.metric_name === form.metric_name)
    .slice()
    .sort((left, right) => left.test_date.localeCompare(right.test_date)),
)

const teamRangeMetricRecords = computed<MetricRangePoint[]>(() => {
  const grouped = records.value
    .filter((item) => item.metric_name === form.metric_name)
    .reduce(
      (accumulator: Map<string, { total: number; count: number; min: number; max: number }>, item) => {
        const value = Number(item.result_value || 0)
        const entry = accumulator.get(item.test_date) || { total: 0, count: 0, min: value, max: value }
        entry.total += value
        entry.count += 1
        entry.min = Math.min(entry.min, value)
        entry.max = Math.max(entry.max, value)
        accumulator.set(item.test_date, entry)
        return accumulator
      },
      new Map<string, { total: number; count: number; min: number; max: number }>(),
    )

  return Array.from(grouped.entries())
    .map(([testDate, entry]) => ({
      test_date: testDate,
      average_value: Number((entry.total / entry.count).toFixed(2)),
      min_value: Number(entry.min.toFixed(2)),
      max_value: Number(entry.max.toFixed(2)),
    }))
    .sort((left, right) => left.test_date.localeCompare(right.test_date))
})

const chartDates = computed<string[]>(() =>
  Array.from(
    new Set([
      ...selectedMetricRecords.value.map((item) => item.test_date),
      ...teamRangeMetricRecords.value.map((item) => item.test_date),
    ]),
  ).sort((left, right) => left.localeCompare(right)),
)

const chartTitle = computed(() => {
  const athleteName = selectedAthlete.value?.full_name || '当前运动员'
  return `${athleteName} - ${form.metric_name} 趋势`
})

const totalLibraryRecords = computed(() =>
  records.value
    .filter((record) => {
      const athleteName = record.athlete?.full_name || ''
      const athleteMatch = !libraryFilters.athleteKeyword || athleteName.includes(libraryFilters.athleteKeyword.trim())
      const metricMatch = !libraryFilters.metricKeyword || record.metric_name.includes(libraryFilters.metricKeyword.trim())
      const typeMatch = !libraryFilters.testType || record.test_type === libraryFilters.testType
      return athleteMatch && metricMatch && typeMatch
    })
    .slice()
    .sort((left, right) => {
      const dateCompare = right.test_date.localeCompare(left.test_date)
      if (dateCompare !== 0) return dateCompare
      return right.id - left.id
    }),
)

const hasLibraryFilters = computed(
  () => Boolean(libraryFilters.athleteKeyword.trim() || libraryFilters.metricKeyword.trim() || libraryFilters.testType),
)

const libraryAthleteOptions = computed(() =>
  Array.from(new Set(records.value.map((record) => record.athlete?.full_name || '').filter(Boolean))).sort((left, right) =>
    left.localeCompare(right, 'zh-CN'),
  ),
)

const libraryMetricOptions = computed(() =>
  Array.from(new Set(records.value.map((record) => record.metric_name).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right, 'zh-CN'),
  ),
)

async function hydrate() {
  loading.value = true
  ;[athletes.value, records.value] = await Promise.all([fetchAthletes(), fetchTestRecords()])
  if (!form.athlete_id && athletes.value[0]) {
    form.athlete_id = athletes.value[0].id
  }
  loading.value = false
  await nextTick()
  renderChart()
}

async function submit() {
  await createTestRecord({ ...form, result_text: form.result_text || null })
  actionMessage.value = '测试记录已保存。'
  await hydrate()
}

async function handleTemplateDownload() {
  templateBusy.value = true
  actionMessage.value = ''
  try {
    const blob = await downloadTestRecordTemplate()
    downloadBlob(blob, 'test-record-import-template.xlsx')
    actionMessage.value = '导入模板已下载。'
  } finally {
    templateBusy.value = false
  }
}

async function handleLibraryExport() {
  exportBusy.value = true
  actionMessage.value = ''
  try {
    const blob = await exportTestRecordLibrary()
    downloadBlob(blob, 'test-record-library.xlsx')
    actionMessage.value = '测试数据总库已导出。'
  } finally {
    exportBusy.value = false
  }
}

async function handleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  importBusy.value = true
  actionMessage.value = ''
  try {
    const summary = await importTestRecords(file)
    actionMessage.value = `导入完成：共 ${summary.total_rows} 行，新增 ${summary.imported_rows} 行，跳过 ${summary.skipped_rows} 行重复数据。`
    await hydrate()
  } catch (error) {
    actionMessage.value = extractErrorMessage(error)
  } finally {
    importBusy.value = false
    input.value = ''
  }
}

function triggerImport() {
  importInputRef.value?.click()
}

async function handleDeleteFilteredBatch() {
  if (!hasLibraryFilters.value) {
    actionMessage.value = '请先筛选出要删除的测试批次，再执行删除。'
    return
  }
  if (!totalLibraryRecords.value.length) {
    actionMessage.value = '当前筛选条件下没有可删除的测试数据。'
    return
  }

  const dateValues = totalLibraryRecords.value.map((record) => record.test_date).sort((left, right) => left.localeCompare(right))
  const confirmed = confirmDangerousAction({
    title: '批量删除测试数据',
    impactLines: [
      `将删除当前筛选结果 ${totalLibraryRecords.value.length} 条`,
      `日期范围：${dateValues[0]} ~ ${dateValues[dateValues.length - 1]}`,
      `筛选条件：${libraryFilters.athleteKeyword || '全部运动员'} / ${libraryFilters.metricKeyword || '全部项目'} / ${libraryFilters.testType || '全部类型'}`,
    ],
  })
  if (!confirmed) return

  try {
    const result = await deleteTestRecordsBatch(
      totalLibraryRecords.value.map((record) => record.id),
      { confirmed: true, actor_name: '管理端' },
    )
    actionMessage.value = `已删除 ${result.deleted_count} 条测试数据。`
    await hydrate()
  } catch (error) {
    actionMessage.value = extractErrorMessage(error)
  }
}

function computeRelativeStrength(record: TestRecord) {
  const athleteWeight = record.athlete?.weight
  if (!ratioMetrics.has(record.metric_name) || !athleteWeight) return null
  return Number(record.result_value / athleteWeight).toFixed(2)
}

function displayResult(record: TestRecord) {
  if (record.result_text) {
    return record.result_text
  }
  return `${record.result_value} ${record.unit}`
}

function renderChart() {
  if (!chartRef.value) return
  chart ||= echarts.init(chartRef.value)

  const athleteData = new Map<string, number>(selectedMetricRecords.value.map((item) => [item.test_date, Number(item.result_value)]))
  const averageData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.average_value]))
  const minData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.min_value]))
  const maxData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.max_value]))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: Array<{ axisValueLabel: string }>) => {
        const axisLabel = params?.[0]?.axisValueLabel || ''
        const unit = form.unit || unitMap[form.metric_name] || ''
        return [
          axisLabel,
          `个人成绩：${formatTooltipValue(athleteData.get(axisLabel))} ${unit}`.trim(),
          `全队平均：${formatTooltipValue(averageData.get(axisLabel))} ${unit}`.trim(),
          `全队最高：${formatTooltipValue(maxData.get(axisLabel))} ${unit}`.trim(),
          `全队最低：${formatTooltipValue(minData.get(axisLabel))} ${unit}`.trim(),
        ].join('<br/>')
      },
    },
    legend: { data: ['个人成绩', '全队平均', '全队区间'] },
    grid: { left: 56, right: 24, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: chartDates.value },
    yAxis: { type: 'value', name: form.unit || unitMap[form.metric_name] || '' },
    series: [
      {
        type: 'custom',
        name: '全队区间',
        data: [0],
        silent: true,
        tooltip: { show: false },
        renderItem: (_params: unknown, api: any) => {
          const upperPoints = chartDates.value
            .map((dateLabel, index) => {
              const value = maxData.get(dateLabel)
              return value == null ? null : api.coord([index, value])
            })
            .filter(Boolean)
          const lowerPoints = chartDates.value
            .slice()
            .reverse()
            .map((dateLabel) => {
              const value = minData.get(dateLabel)
              if (value == null) return null
              const index = chartDates.value.indexOf(dateLabel)
              return api.coord([index, value])
            })
            .filter(Boolean)

          if (upperPoints.length === 1 && lowerPoints.length === 1) {
            const [upperX, upperY] = upperPoints[0] as [number, number]
            const [, lowerY] = lowerPoints[0] as [number, number]
            const bandHalfWidth = 14

            return {
              type: 'rect',
              shape: {
                x: upperX - bandHalfWidth,
                y: upperY,
                width: bandHalfWidth * 2,
                height: Math.max(lowerY - upperY, 2),
              },
              style: { fill: 'rgba(245,158,11,0.34)' },
            }
          }

          if (upperPoints.length < 2 || lowerPoints.length < 2) return null
          return {
            type: 'polygon',
            shape: { points: [...upperPoints, ...lowerPoints] },
            style: { fill: 'rgba(245,158,11,0.34)' },
          }
        },
      },
      {
        type: 'line',
        smooth: true,
        name: '__max__',
        data: chartDates.value.map((dateLabel) => maxData.get(dateLabel) ?? null),
        lineStyle: { color: 'rgba(245,158,11,0.88)', width: 2 },
        itemStyle: { color: 'rgba(245,158,11,0.96)', borderColor: '#ffffff', borderWidth: 1 },
        symbol: 'circle',
        symbolSize: 8,
        tooltip: { show: false },
        emphasis: { disabled: true },
        connectNulls: false,
      },
      {
        type: 'line',
        smooth: true,
        name: '__min__',
        data: chartDates.value.map((dateLabel) => minData.get(dateLabel) ?? null),
        lineStyle: { color: 'rgba(245,158,11,0.88)', width: 2 },
        itemStyle: { color: 'rgba(245,158,11,0.96)', borderColor: '#ffffff', borderWidth: 1 },
        symbol: 'circle',
        symbolSize: 8,
        tooltip: { show: false },
        emphasis: { disabled: true },
        connectNulls: false,
      },
      {
        type: 'line',
        smooth: true,
        name: '全队平均',
        data: chartDates.value.map((dateLabel) => averageData.get(dateLabel) ?? null),
        lineStyle: { color: '#f59e0b', width: 2.5, type: 'dashed' },
        itemStyle: { color: '#f59e0b' },
        symbolSize: 6,
        connectNulls: false,
        z: 4,
      },
      {
        type: 'line',
        smooth: true,
        name: '个人成绩',
        data: chartDates.value.map((dateLabel) => athleteData.get(dateLabel) ?? null),
        lineStyle: { color: '#0f766e', width: 3 },
        itemStyle: { color: '#0f766e' },
        symbolSize: 7,
        connectNulls: false,
        z: 5,
      },
    ],
  })
}

function extractErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) return detail.join('；')
    if (typeof detail === 'string') return detail
    if (error.message) return error.message
  }
  return '操作失败，请检查导入文件格式。'
}

function formatTooltipValue(value: unknown) {
  if (value == null || value === '') return '--'
  return value
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(url)
}

watch(
  () => form.metric_name,
  (metricName) => {
    form.unit = unitMap[metricName] || 'kg'
  },
  { immediate: true },
)

watch([selectedMetricRecords, teamRangeMetricRecords], async () => {
  await nextTick()
  renderChart()
})

onMounted(hydrate)
</script>

<template>
  <AppShell>
    <div class="page-grid">
      <div class="split-view">
        <div class="panel form-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">测试录入</p>
              <h3>测试数据录入与导入</h3>
            </div>
            <div class="action-stack">
              <button class="ghost-btn" :disabled="templateBusy" @click="handleTemplateDownload">
                {{ templateBusy ? '下载中...' : '下载导入模板' }}
              </button>
              <button class="ghost-btn" :disabled="importBusy" @click="triggerImport">
                {{ importBusy ? '导入中...' : '导入测试数据 Excel' }}
              </button>
            </div>
          </div>

          <input ref="importInputRef" class="hidden-input" type="file" accept=".xlsx" @change="handleImport" />

          <p class="hint-text">
            先下载 Excel 模板，按模板填写后导入。导入会校验运动员姓名和字段格式；重复数据会自动跳过。
          </p>

          <p v-if="actionMessage" class="status-banner">{{ actionMessage }}</p>

          <label class="field">
            <span>运动员</span>
            <select v-model.number="form.athlete_id" class="text-input">
              <option v-for="athlete in athletes" :key="athlete.id" :value="athlete.id">{{ athlete.full_name }}</option>
            </select>
          </label>

          <div v-if="selectedAthlete" class="athlete-meta">
            <span>{{ selectedAthlete.team?.name || '未分队' }}</span>
            <span>体重：{{ selectedAthlete.weight ?? '--' }} kg</span>
          </div>

          <label class="field">
            <span>测试日期</span>
            <input v-model="form.test_date" type="date" class="text-input" />
          </label>

          <div class="two-col">
            <label class="field">
              <span>测试类型</span>
              <select v-model="form.test_type" class="text-input">
                <option v-for="option in testTypeOptions" :key="option" :value="option">{{ option }}</option>
              </select>
            </label>

            <label class="field">
              <span>测试项目</span>
              <select v-model="form.metric_name" class="text-input">
                <option v-for="option in metricOptions" :key="option" :value="option">{{ option }}</option>
              </select>
            </label>
          </div>

          <div class="two-col">
            <label class="field">
              <span>数值结果</span>
              <input v-model.number="form.result_value" type="number" step="0.01" class="text-input" placeholder="用于计算和统计" />
            </label>
            <label class="field">
              <span>显示文本</span>
              <input v-model="form.result_text" class="text-input" placeholder="如 13′32″3，可留空" />
            </label>
          </div>

          <div class="two-col">
            <label class="field">
              <span>单位</span>
              <input v-model="form.unit" class="text-input" />
            </label>
            <label class="field">
              <span>备注</span>
              <input v-model="form.notes" class="text-input" placeholder="可选" />
            </label>
          </div>

          <button class="primary-btn" @click="submit">保存测试记录</button>
        </div>

        <div class="panel chart-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">趋势图</p>
              <h3>{{ chartTitle }}</h3>
            </div>
          </div>

          <div ref="chartRef" class="chart"></div>

          <div class="list-grid">
            <div v-for="record in selectedAthleteRecords" :key="record.id" class="row-card adaptive-card">
              <strong class="adaptive-card-title">{{ record.metric_name }}：{{ displayResult(record) }}</strong>
              <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ record.test_date }} / {{ record.test_type }}</span>
              <small v-if="computeRelativeStrength(record)" class="adaptive-card-meta adaptive-card-clamp-1">
                力量体重比：{{ computeRelativeStrength(record) }}
              </small>
              <small v-else class="adaptive-card-meta adaptive-card-clamp-1">{{ record.notes || '无备注' }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="panel library-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">数据总库</p>
            <h3>测试数据总库</h3>
          </div>
          <div class="action-stack">
            <button
              class="ghost-btn danger-btn"
              :disabled="!hasLibraryFilters || !totalLibraryRecords.length"
              @click="handleDeleteFilteredBatch"
            >
              删除当前筛选批次
            </button>
            <button class="ghost-btn" :disabled="exportBusy" @click="handleLibraryExport">
              {{ exportBusy ? '导出中...' : '导出总库 Excel' }}
            </button>
          </div>
        </div>

        <div class="filter-grid">
          <input
            v-model="libraryFilters.athleteKeyword"
            class="text-input"
            list="library-athlete-options"
            placeholder="按运动员姓名搜索或选择"
          />
          <datalist id="library-athlete-options">
            <option v-for="option in libraryAthleteOptions" :key="option" :value="option" />
          </datalist>
          <input
            v-model="libraryFilters.metricKeyword"
            class="text-input"
            list="library-metric-options"
            placeholder="按测试项目搜索或选择"
          />
          <datalist id="library-metric-options">
            <option v-for="option in libraryMetricOptions" :key="option" :value="option" />
          </datalist>
          <select v-model="libraryFilters.testType" class="text-input">
            <option value="">全部测试类型</option>
            <option v-for="option in testTypeOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>

        <div class="library-meta">
          <span>总记录：{{ records.length }}</span>
          <span>筛选后：{{ totalLibraryRecords.length }}</span>
          <span>运动员：{{ athletes.length }}</span>
        </div>

        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>运动员</th>
                <th>队伍</th>
                <th>测试类型</th>
                <th>测试项目</th>
                <th>数值结果</th>
                <th>显示文本</th>
                <th>单位</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in totalLibraryRecords" :key="record.id">
                <td>{{ record.test_date }}</td>
                <td>{{ record.athlete?.full_name || '-' }}</td>
                <td>{{ record.athlete?.team?.name || '-' }}</td>
                <td>{{ record.test_type }}</td>
                <td>{{ record.metric_name }}</td>
                <td>{{ record.result_value }}</td>
                <td>{{ record.result_text || '-' }}</td>
                <td>{{ record.unit }}</td>
                <td>{{ record.notes || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="!loading && totalLibraryRecords.length === 0" class="hint-text">当前筛选条件下没有测试数据。</p>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.page-grid {
  display: grid;
  gap: 18px;
  align-content: start;
}

.split-view {
  display: grid;
  grid-template-columns: minmax(360px, 430px) 1fr;
  gap: 18px;
  min-height: 0;
}

.form-panel,
.chart-panel,
.library-panel,
.field,
.list-grid {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 0;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}

.action-stack {
  display: grid;
  gap: 10px;
}

.ghost-btn {
  min-height: 44px;
  border-radius: 14px;
  padding: 0 14px;
  background: #e2e8f0;
  color: #0f172a;
  font-weight: 600;
}

.danger-btn {
  color: #b91c1c;
}

.hidden-input {
  display: none;
}

.eyebrow,
.field span,
.athlete-meta span,
.library-meta span {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.hint-text {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.status-banner {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #ecfdf5;
  color: #065f46;
  font-size: 13px;
}

.athlete-meta,
.library-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.two-col,
.filter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.filter-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.chart-panel {
  grid-template-rows: auto auto auto;
}

.chart {
  height: 320px;
  width: 100%;
}

.list-grid {
  overflow-y: auto;
  max-height: 360px;
  padding-right: 8px;
}

.row-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px;
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 8px;
  min-height: 112px;
}

.library-panel {
  align-content: start;
}

.table-scroll {
  overflow: auto;
  max-height: 560px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: white;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 920px;
}

.data-table th,
.data-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

.data-table th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  z-index: 1;
}

@media (max-width: 1100px) {
  .split-view,
  .two-col,
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
