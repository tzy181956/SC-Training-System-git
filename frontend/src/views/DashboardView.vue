<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import StatCard from '@/components/common/StatCard.vue'
import AppShell from '@/components/layout/AppShell.vue'
import { useAthletesStore } from '@/stores/athletes'
import { usePlansStore } from '@/stores/plans'

const router = useRouter()
const athletesStore = useAthletesStore()
const plansStore = usePlansStore()

onMounted(async () => {
  await Promise.all([athletesStore.hydrate(), plansStore.hydrate()])
})

const activeAssignments = computed(() => plansStore.assignments.filter((item) => item.status === 'active').length)
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

    <div class="panel dashboard-panels">
      <button class="simple-card action-card" @click="router.push({ name: 'athletes' })">
        <strong>运动员管理</strong>
        <span>维护基础资料、所属队伍、位置、训练等级和备注。</span>
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
