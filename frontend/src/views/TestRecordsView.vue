<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

import { fetchAthletes } from '@/api/athletes'
import { createTestRecord, fetchTestRecords } from '@/api/testRecords'
import AppShell from '@/components/layout/AppShell.vue'
import { todayString } from '@/utils/date'

type MetricRangePoint = {
  test_date: string
  average_value: number
  min_value: number
  max_value: number
}

const athletes = ref<any[]>([])
const records = ref<any[]>([])
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const testTypeOptions = ['基础身体', '力量测试', '体能测试', '速度测试', '耐力测试']
const metricOptions = ['卧推', '卧拉', '深蹲', '抓举', '引体向上', '反向跳', '静蹲跳', '直腿跳', '助跑摸高', '原地摸高']
const unitMap: Record<string, string> = {
  卧推: 'kg',
  卧拉: 'kg',
  深蹲: 'kg',
  抓举: 'kg',
  引体向上: '次',
  反向跳: 'cm',
  静蹲跳: 'cm',
  直腿跳: 'RSI',
  助跑摸高: 'cm',
  原地摸高: 'cm',
}
const ratioMetrics = new Set(['卧推', '卧拉', '深蹲', '抓举'])

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
      (accumulator: Map<string, { total: number; count: number; min: number; max: number }>, item: any) => {
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

async function hydrate() {
  ;[athletes.value, records.value] = await Promise.all([fetchAthletes(), fetchTestRecords()])
  if (!form.athlete_id && athletes.value[0]) form.athlete_id = athletes.value[0].id
  await nextTick()
  renderChart()
}

async function submit() {
  await createTestRecord({ ...form, result_text: form.result_text || null })
  await hydrate()
}

function computeRelativeStrength(record: any) {
  const athleteWeight = record.athlete?.weight
  if (!ratioMetrics.has(record.metric_name) || !athleteWeight) return null
  return Number(record.result_value / athleteWeight).toFixed(2)
}

function displayResult(record: any) {
  if (record.result_text) {
    return record.result_text
  }
  return `${record.result_value} ${record.unit}`
}

function formatTooltipValue(value: unknown) {
  if (value == null || value === '') return '--'
  return value
}

function renderChart() {
  if (!chartRef.value) return
  chart ||= echarts.init(chartRef.value)

  const athleteData = new Map<string, number>(selectedMetricRecords.value.map((item: any) => [item.test_date, Number(item.result_value)]))
  const averageData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.average_value]))
  const minData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.min_value]))
  const maxData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.max_value]))
  const rangeData = new Map<string, number>(
    teamRangeMetricRecords.value.map((item) => [item.test_date, Number((item.max_value - item.min_value).toFixed(2))]),
  )

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
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
        tooltip: { show: false },
        emphasis: { disabled: true },
        silent: true,
        z: 1,
        renderItem: (_params: any, api: any) => {
          const upperPoints = chartDates.value
            .map((date, index) => {
              const value = maxData.get(date)
              if (value == null) return null
              return api.coord([index, value])
            })
            .filter(Boolean)

          const lowerPoints = chartDates.value
            .slice()
            .reverse()
            .map((date) => {
              const value = minData.get(date)
              if (value == null) return null
              const index = chartDates.value.indexOf(date)
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
              style: {
                fill: 'rgba(245,158,11,0.34)',
              },
            }
          }

          if (upperPoints.length < 2 || lowerPoints.length < 2) {
            return null
          }

          return {
            type: 'polygon',
            shape: {
              points: [...upperPoints, ...lowerPoints],
            },
            style: {
              fill: 'rgba(245,158,11,0.34)',
            },
          }
        },
      },
      {
        type: 'line',
        smooth: true,
        name: '__max__',
        data: chartDates.value.map((date) => maxData.get(date) ?? null),
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
        data: chartDates.value.map((date) => minData.get(date) ?? null),
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
        data: chartDates.value.map((date) => averageData.get(date) ?? null),
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
        data: chartDates.value.map((date) => athleteData.get(date) ?? null),
        lineStyle: { color: '#0f766e', width: 3 },
        itemStyle: { color: '#0f766e' },
        symbolSize: 7,
        connectNulls: false,
        z: 5,
      },
    ],
  })
}

watch(
  () => form.metric_name,
  (metricName) => {
    form.unit = unitMap[metricName] || 'kg'
  },
  { immediate: true },
)

watch([selectedMetricRecords, teamRangeMetricRecords], () => renderChart())
onMounted(hydrate)
</script>

<template>
  <AppShell>
    <div class="split-view">
      <div class="panel form-panel">
        <div>
          <p class="eyebrow">测试录入</p>
          <h3>测试数据记录</h3>
        </div>

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
            <input v-model.number="form.result_value" type="number" step="0.01" class="text-input" placeholder="用于计算的数值" />
          </label>
          <label class="field">
            <span>展示文本</span>
            <input v-model="form.result_text" class="text-input" placeholder="如 12''9，没有可留空" />
          </label>
        </div>

        <div class="two-col">
          <label class="field">
            <span>单位</span>
            <input v-model="form.unit" class="text-input" />
          </label>
          <label class="field">
            <span>备注</span>
            <input v-model="form.notes" class="text-input" placeholder="可选备注" />
          </label>
        </div>

        <button class="primary-btn" @click="submit">保存测试记录</button>
      </div>

      <div class="panel chart-panel">
        <div class="chart-head">
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
  </AppShell>
</template>

<style scoped>
.split-view {
  display: grid;
  grid-template-columns: minmax(360px, 420px) 1fr;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.form-panel,
.chart-panel,
.field,
.list-grid {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 0;
}

.form-panel,
.chart-panel {
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.eyebrow,
.field span,
.athlete-meta span {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.athlete-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.chart {
  height: 320px;
  width: 100%;
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

.two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 1100px) {
  .split-view,
  .two-col {
    grid-template-columns: 1fr;
  }

  .split-view {
    height: auto;
  }
}
</style>
