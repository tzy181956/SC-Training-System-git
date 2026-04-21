<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import {
  createExercise,
  deleteExercise,
  fetchExerciseCategoriesTree,
  fetchExercises,
  updateExercise,
} from '@/api/exercises'
import ExerciseLibraryEditor from '@/components/exercise/ExerciseLibraryEditor.vue'
import AppShell from '@/components/layout/AppShell.vue'
import type { ExerciseCategoryNode, ExerciseLibraryItem } from '@/types/exerciseLibrary'
import {
  EXERCISE_TAG_FACETS,
  buildExerciseLibraryFacets,
  filterExerciseLibrary,
  getLevel1Options,
  getLevel2Options,
  summarizeExerciseTags,
} from '@/utils/exerciseLibrary'

const exercises = ref<ExerciseLibraryItem[]>([])
const categoryTree = ref<ExerciseCategoryNode[]>([])
const selected = ref<ExerciseLibraryItem | null>(null)
const layoutRef = ref<HTMLElement | null>(null)
const layoutHeight = ref<number | null>(null)

const filters = reactive({
  keyword: '',
  level1: '',
  level2: '',
  tags: Object.fromEntries(EXERCISE_TAG_FACETS.map(({ key }) => [key, [] as string[]])),
})

const level1Options = computed(() => getLevel1Options(exercises.value))
const level2Options = computed(() => getLevel2Options(exercises.value, filters.level1))
const facetOptions = computed(() => buildExerciseLibraryFacets(exercises.value))
const hasActiveFilters = computed(() => {
  if (filters.keyword.trim()) return true
  if (filters.level1) return true
  if (filters.level2) return true
  return Object.values(filters.tags).some((values) => values.length > 0)
})
const filteredExercises = computed(() => {
  if (!hasActiveFilters.value) return []
  return filterExerciseLibrary(exercises.value, filters)
})

async function hydrate(preferredId?: number | null) {
  const [exerciseData, categoryData] = await Promise.all([fetchExercises(), fetchExerciseCategoriesTree()])
  exercises.value = exerciseData
  categoryTree.value = categoryData
  if (!hasActiveFilters.value) {
    selected.value = null
    return
  }
  if (preferredId) {
    selected.value = exercises.value.find((item) => item.id === preferredId) || null
    return
  }
  if (!selected.value && filteredExercises.value[0]) selected.value = filteredExercises.value[0]
}

async function handleSave(payload: Record<string, unknown>) {
  if (selected.value?.id) {
    await updateExercise(selected.value.id, payload)
    await hydrate(selected.value.id)
    return
  }
  const created = await createExercise(payload)
  await hydrate(created.id)
}

async function handleDelete(exerciseId: number) {
  try {
    await deleteExercise(exerciseId)
    await hydrate()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    window.alert(typeof detail === 'string' ? detail : '删除动作失败，请稍后再试。')
  }
}

function clearFilters() {
  filters.keyword = ''
  filters.level1 = ''
  filters.level2 = ''
  Object.keys(filters.tags).forEach((key) => {
    filters.tags[key] = []
  })
}

function toggleTagFilter(key: string, value: string) {
  const current = new Set(filters.tags[key] || [])
  if (current.has(value)) current.delete(value)
  else current.add(value)
  filters.tags[key] = Array.from(current)
}

function createCustomExercise() {
  selected.value = null
}

function updateLayoutHeight() {
  if (!layoutRef.value || typeof window === 'undefined') return
  const top = layoutRef.value.getBoundingClientRect().top
  const available = Math.floor(window.innerHeight - top - 24)
  layoutHeight.value = available > 320 ? available : null
}

function syncSelectionWithFilters() {
  if (!hasActiveFilters.value) {
    selected.value = null
    return
  }

  if (selected.value && filteredExercises.value.some((item) => item.id === selected.value?.id)) {
    return
  }

  selected.value = filteredExercises.value[0] || null
}

watch(
  () => [
    hasActiveFilters.value,
    filters.keyword,
    filters.level1,
    filters.level2,
    ...Object.values(filters.tags).map((values) => values.join('|')),
    exercises.value.length,
  ],
  () => {
    syncSelectionWithFilters()
  },
)

onMounted(() => hydrate())
onMounted(() => {
  nextTick(() => updateLayoutHeight())
  window.addEventListener('resize', updateLayoutHeight)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateLayoutHeight)
})

watch(
  () => selected.value?.id,
  () => nextTick(() => updateLayoutHeight()),
)
</script>

<template>
  <AppShell>
    <div ref="layoutRef" class="library-layout" :style="layoutHeight ? { '--library-layout-height': `${layoutHeight}px` } : {}">
      <section class="panel filter-panel">
        <div class="toolbar">
          <div>
            <p class="eyebrow">动作库</p>
            <h3>EXOS 动作库</h3>
          </div>
          <div class="toolbar-actions">
            <button class="primary-btn slim" @click="createCustomExercise">新建动作</button>
          </div>
        </div>

        <div class="grid search-grid">
          <label class="field">
            <span class="field-label">关键词搜索</span>
            <input
              v-model="filters.keyword"
              class="text-input"
              placeholder="动作名称 / 英文名 / 检索词 / 标签词条"
            />
          </label>
          <label class="field">
            <span class="field-label">一级分类</span>
            <select v-model="filters.level1" class="text-input">
              <option value="">全部一级分类</option>
              <option v-for="option in level1Options" :key="option" :value="option">{{ option }}</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">二级分类</span>
            <select v-model="filters.level2" class="text-input">
              <option value="">全部二级分类</option>
              <option v-for="option in level2Options" :key="option" :value="option">{{ option }}</option>
            </select>
          </label>
        </div>

        <div class="filter-actions">
          <span>{{ hasActiveFilters ? `筛选后 ${filteredExercises.length} / ${exercises.length}` : `请先筛选（当前总数 ${exercises.length}）` }}</span>
          <button class="ghost-btn slim" @click="clearFilters">清空筛选</button>
        </div>

        <div class="facet-panel">
          <div v-for="facet in EXERCISE_TAG_FACETS" :key="facet.key" class="facet-group">
            <strong>{{ facet.label }}</strong>
            <div class="facet-options">
              <button
                v-for="option in facetOptions[facet.key] || []"
                :key="option"
                class="facet-chip"
                :class="{ active: filters.tags[facet.key].includes(option) }"
                @click="toggleTagFilter(facet.key, option)"
              >
                {{ option }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section class="panel list-panel">
        <div class="list-head">
          <div>
            <p class="eyebrow">动作列表</p>
            <h3>{{ hasActiveFilters ? '筛选结果' : '等待筛选' }}</h3>
          </div>
        </div>
        <div class="list-scroll">
          <button
            v-for="exercise in filteredExercises"
            :key="exercise.id"
            class="exercise-row adaptive-card"
            :class="{ active: selected?.id === exercise.id }"
            @click="selected = exercise"
          >
            <div class="row-head">
              <strong class="adaptive-card-title">{{ exercise.name }}</strong>
              <span class="source-badge" :class="exercise.source_type">{{ exercise.source_type === 'exos_excel' ? 'Excel' : '自定义' }}</span>
            </div>
            <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ exercise.name_en || exercise.alias || '无英文名' }}</span>
            <small class="adaptive-card-meta adaptive-card-clamp-2">
              {{ exercise.level1_category || '未分类' }} / {{ exercise.level2_category || '未分类' }} / {{ exercise.base_movement || '未分类' }}
            </small>
            <small class="adaptive-card-meta adaptive-card-clamp-2">{{ exercise.category_path || '无分类路径' }}</small>
            <div class="tag-line">
              <span v-for="tag in summarizeExerciseTags(exercise)" :key="tag" class="tag-chip">{{ tag }}</span>
            </div>
          </button>
          <div v-if="!hasActiveFilters" class="empty-state">请先搜索或选择分类/标签后再显示动作。</div>
          <div v-else-if="!filteredExercises.length" class="empty-state">当前筛选条件下没有动作。</div>
        </div>
      </section>

      <ExerciseLibraryEditor
        class="editor-panel"
        :model-value="selected"
        :category-tree="categoryTree"
        :facet-options="facetOptions"
        @submit="handleSave"
        @remove="handleDelete"
      />
    </div>
  </AppShell>
</template>

<style scoped>
.library-layout {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(360px, 520px) 1fr;
  gap: 18px;
  align-items: stretch;
  min-height: var(--library-layout-height, auto);
  height: var(--library-layout-height, auto);
  max-height: var(--library-layout-height, none);
}

.filter-panel,
.list-panel,
.editor-panel {
  min-height: 0;
  height: 100%;
}

.filter-panel,
.list-panel {
  display: grid;
  gap: 14px;
  align-content: start;
}

.filter-panel {
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.list-panel {
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}

.toolbar,
.toolbar-actions,
.filter-actions,
.list-head,
.search-grid,
.facet-group,
.facet-options,
.row-head,
.tag-line {
  display: flex;
  gap: 10px;
}

.toolbar,
.filter-actions,
.list-head,
.row-head {
  align-items: center;
  justify-content: space-between;
}

.toolbar {
  align-items: start;
}

.toolbar-actions,
.facet-options,
.tag-line {
  flex-wrap: wrap;
}

.search-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 12px;
}

.facet-panel,
.facet-group {
  display: grid;
  gap: 10px;
}

.facet-group {
  padding-top: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.facet-chip,
.tag-chip,
.source-badge {
  min-height: 32px;
  border-radius: 999px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
}

.facet-chip,
.tag-chip {
  background: #e2e8f0;
}

.facet-chip.active {
  background: var(--primary);
  color: white;
}

.source-badge {
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
}

.source-badge.custom_manual {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.list-scroll {
  min-height: 0;
  max-height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
  display: grid;
  gap: 12px;
  padding-right: 8px;
}

.exercise-row {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px;
  text-align: left;
  display: grid;
  gap: 8px;
}

.exercise-row.active {
  background: #d1fae5;
}

.empty-state {
  padding: 20px 16px;
  text-align: center;
  color: var(--muted);
  border: 1px dashed var(--line);
  border-radius: 16px;
}

.eyebrow {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

@media (max-width: 1400px) {
  .library-layout {
    grid-template-columns: 1fr;
    min-height: auto;
    height: auto;
    max-height: none;
  }

  .search-grid {
    grid-template-columns: 1fr;
  }
}
</style>
