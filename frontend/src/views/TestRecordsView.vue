<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

import { fetchAthletes } from '@/api/athletes'
import { createTestRecord, fetchTestRecords } from '@/api/testRecords'
import AppShell from '@/components/layout/AppShell.vue'
import { todayString } from '@/utils/date'

const athletes = ref<any[]>([])
const records = ref<any[]>([])
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const testTypeOptions = ['力量测试', '体能测试', '速度测试', '恢复评估']
const metricOptions = ['深蹲 1RM', '卧推 1RM', '硬拉 1RM', '反向纵跳', '30 米冲刺', '哑铃推举 6RM']
const unitMap: Record<string, string> = {
  '深蹲 1RM': '公斤',
  '卧推 1RM': '公斤',
  '硬拉 1RM': '公斤',
  '反向纵跳': '厘米',
  '30 米冲刺': '秒',
  '哑铃推举 6RM': '公斤',
}

const form = reactive({
  athlete_id: 0,
  test_date: todayString(),
  test_type: '力量测试',
  metric_name: '深蹲 1RM',
  result_value: 0,
  unit: '公斤',
  notes: '',
})

const selectedAthleteRecords = computed(() =>
  records.value.filter((item) => !form.athlete_id || item.athlete_id === form.athlete_id),
)

async function hydrate() {
  ;[athletes.value, records.value] = await Promise.all([fetchAthletes(), fetchTestRecords()])
  if (!form.athlete_id && athletes.value[0]) form.athlete_id = athletes.value[0].id
  await nextTick()
  renderChart()
}

async function submit() {
  await createTestRecord({ ...form })
  await hydrate()
}

function renderChart() {
  if (!chartRef.value) return
  chart ||= echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: selectedAthleteRecords.value.map((item) => item.test_date) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        smooth: true,
        data: selectedAthleteRecords.value.map((item) => item.result_value),
        areaStyle: { color: 'rgba(15,118,110,0.15)' },
        lineStyle: { color: '#0f766e' },
      },
    ],
  })
}

watch(
  () => form.metric_name,
  (metricName) => {
    form.unit = unitMap[metricName] || '公斤'
  },
  { immediate: true },
)

watch(selectedAthleteRecords, () => renderChart())
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
            <span>测试成绩</span>
            <input v-model.number="form.result_value" type="number" class="text-input" placeholder="请输入测试结果" />
          </label>
          <label class="field">
            <span>单位</span>
            <input v-model="form.unit" class="text-input" />
          </label>
        </div>
        <label class="field">
          <span>备注</span>
          <textarea v-model="form.notes" class="text-input area" placeholder="例如：季前测试、伤后回归、比赛周评估" />
        </label>
        <button class="primary-btn" @click="submit">保存测试记录</button>
      </div>
      <div class="panel chart-panel">
        <div class="chart-head">
          <div>
            <p class="eyebrow">趋势图</p>
            <h3>最近测试变化</h3>
          </div>
        </div>
        <div ref="chartRef" class="chart"></div>
        <div class="list-grid">
          <div v-for="record in selectedAthleteRecords" :key="record.id" class="row-card">
            <strong>{{ record.metric_name }}：{{ record.result_value }} {{ record.unit }}</strong>
            <span>{{ record.test_date }} / {{ record.test_type }}</span>
            <small>{{ record.notes || '无备注' }}</small>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.split-view {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 18px;
}

.form-panel,
.chart-panel,
.field,
.list-grid {
  display: grid;
  gap: 12px;
  align-content: start;
}

.eyebrow,
.field span,
.row-card span,
.row-card small {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
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
  gap: 6px;
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
}
</style>
