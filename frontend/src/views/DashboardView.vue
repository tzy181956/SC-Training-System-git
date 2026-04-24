<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchTrainingSyncIssues, retryTrainingSyncIssue } from '@/api/sessions'
import StatCard from '@/components/common/StatCard.vue'
import AppShell from '@/components/layout/AppShell.vue'
import { useAthletesStore } from '@/stores/athletes'
import { usePlansStore } from '@/stores/plans'

const router = useRouter()
const athletesStore = useAthletesStore()
const plansStore = usePlansStore()
const syncIssues = ref<any[]>([])
const syncNotice = ref('')
const syncNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const retryingIssueId = ref<number | null>(null)

onMounted(async () => {
  await Promise.all([athletesStore.hydrate(), plansStore.hydrate(), loadSyncIssues()])
})

const activeAssignments = computed(() => plansStore.assignments.filter((item) => item.status === 'active').length)

async function loadSyncIssues() {
  syncIssues.value = await fetchTrainingSyncIssues({ issue_status: 'manual_retry_required' })
}

async function retrySyncIssue(issueId: number) {
  retryingIssueId.value = issueId
  try {
    await retryTrainingSyncIssue(issueId)
    syncNotice.value = '同步异常已重试，待处理列表已刷新。'
    syncNoticeTone.value = 'success'
    await loadSyncIssues()
  } catch {
    syncNotice.value = '手动重试失败，请回到训练端设备继续处理。'
    syncNoticeTone.value = 'warning'
  } finally {
    retryingIssueId.value = null
  }
}
</script>

<template>
  <AppShell>
    <div class="hero-grid">
      <section class="hero-card">
        <p class="hero-label">管理模式</p>
        <h3>在这里维护动作库、训练模板、计划分配、训练数据和测试数据</h3>
        <p class="hero-copy">
          当前页面面向教练使用，重点放在制定训练计划、分配周期、查看训练执行结果和维护基础资料。
        </p>
        <div class="hero-actions">
          <button class="primary-btn hero-btn" @click="router.push({ name: 'plans' })">管理训练模板</button>
          <button class="secondary-btn hero-btn" @click="router.push({ name: 'assignments' })">管理计划分配</button>
          <button class="secondary-btn hero-btn" @click="router.push({ name: 'training-reports' })">查看训练数据</button>
        </div>
      </section>
      <section class="hero-side">
        <StatCard label="运动员" :value="athletesStore.athletes.length" hint="当前系统中的运动员总数" />
        <StatCard label="训练模板" :value="plansStore.templates.length" hint="当前可分配模板数量" />
        <StatCard label="进行中计划" :value="activeAssignments" hint="支持同一周期多份计划并行" />
      </section>
    </div>

    <section class="panel sync-issue-panel">
      <div class="sync-issue-head">
        <div>
          <p class="section-label">同步</p>
          <h3>同步异常待处理</h3>
        </div>
        <button class="secondary-btn" type="button" @click="loadSyncIssues">刷新异常</button>
      </div>
      <p v-if="syncNotice" class="sync-notice" :class="syncNoticeTone">{{ syncNotice }}</p>
      <div v-if="syncIssues.length" class="sync-issue-list">
        <article v-for="issue in syncIssues" :key="issue.id" class="sync-issue-card">
          <div class="sync-issue-copy">
            <strong>{{ issue.athlete_name || `运动员 ${issue.athlete_id}` }}｜{{ issue.session_date }}</strong>
            <span>{{ issue.summary }}</span>
            <span v-if="issue.last_error" class="sync-issue-error">最近错误：{{ issue.last_error }}</span>
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
      <div v-else class="sync-empty">当前没有待处理的同步异常。</div>
    </section>

    <div class="panel dashboard-panels">
      <button class="simple-card action-card" @click="router.push({ name: 'athletes' })">
        <strong>运动员管理</strong>
        <span>维护基础资料、所属队伍、位置和备注。</span>
      </button>
      <button class="simple-card action-card" @click="router.push({ name: 'exercises' })">
        <strong>动作库管理</strong>
        <span>维护动作标签、技术要点、视频地址和训练属性。</span>
      </button>
      <button class="simple-card action-card" @click="router.push({ name: 'plans' })">
        <strong>模板管理</strong>
        <span>创建多动作模板，设置负荷方式、组次数和进阶逻辑。</span>
      </button>
      <button class="simple-card action-card" @click="router.push({ name: 'training-reports' })">
        <strong>训练数据</strong>
        <span>查看计划执行情况、组次完成度、主项重量变化和异常提醒。</span>
      </button>
      <button class="simple-card action-card" @click="router.push({ name: 'backups' })">
        <strong>备份恢复</strong>
        <span>查看备份列表，执行整库恢复或某类数据恢复。</span>
      </button>
      <button class="simple-card action-card" @click="router.push({ name: 'tests' })">
        <strong>测试数据</strong>
        <span>记录深蹲、卧推、纵跳、冲刺等测试结果，供分配联动使用。</span>
      </button>
    </div>
  </AppShell>
</template>

<style scoped>
.hero-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 18px;
}

.hero-card {
  background: linear-gradient(135deg, #0f766e, #134e4a);
  color: white;
  border-radius: 24px;
  padding: 24px;
  display: grid;
  gap: 14px;
  box-shadow: var(--shadow);
}

.hero-label,
.hero-copy {
  margin: 0;
  color: rgba(255, 255, 255, 0.84);
}

.hero-card h3 {
  margin: 0;
  font-size: 30px;
}

.hero-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.hero-btn {
  min-height: 60px;
}

.hero-side {
  display: grid;
  gap: 16px;
}

.sync-issue-panel {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.sync-issue-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.section-label {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 13px;
}

.sync-issue-head h3,
.sync-notice,
.sync-issue-copy strong,
.sync-issue-copy span,
.sync-empty {
  margin: 0;
}

.sync-notice {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
}

.sync-notice.success {
  background: #dcfce7;
  color: #166534;
}

.sync-notice.warning {
  background: #fef3c7;
  color: #92400e;
}

.sync-notice.error {
  background: #fee2e2;
  color: #b91c1c;
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
  border-radius: 18px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.28);
}

.sync-issue-copy {
  display: grid;
  gap: 6px;
}

.sync-issue-copy span {
  color: var(--muted);
}

.sync-issue-error {
  color: #92400e;
}

.dashboard-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.simple-card {
  background: var(--panel-soft);
  padding: 18px;
  border-radius: 18px;
  display: grid;
  gap: 8px;
  text-align: left;
}

.simple-card span {
  color: var(--muted);
}

@media (max-width: 1200px) {
  .hero-grid,
  .dashboard-panels,
  .hero-actions {
    grid-template-columns: 1fr;
  }
}
</style>
