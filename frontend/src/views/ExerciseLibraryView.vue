<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import {
  createExercise,
  deleteExercise,
  fetchExercise,
  fetchExerciseCategoriesTree,
  fetchExerciseFacets,
  fetchExercises,
  updateExercise,
} from '@/api/exercises'
import ExerciseCategoryManager from '@/components/exercise/ExerciseCategoryManager.vue'
import ExerciseLibraryEditor from '@/components/exercise/ExerciseLibraryEditor.vue'
import AppShell from '@/components/layout/AppShell.vue'
import { useAuthStore } from '@/stores/auth'
import type {
  ExerciseCategoryNode,
  ExerciseFacetValues,
  ExerciseLibraryItem,
  ExerciseListItem,
  ExerciseListResponse,
} from '@/types/exerciseLibrary'
import { EXERCISE_TAG_FACETS, summarizeExerciseListTags } from '@/utils/exerciseLibrary'

const DEFAULT_PAGE_SIZE = 50
const FILTER_DEBOUNCE_MS = 300

const authStore = useAuthStore()
const categoryTree = ref<ExerciseCategoryNode[]>([])
const exerciseFacets = ref<ExerciseFacetValues>({
  level1_options: [],
  level2_options: [],
  level2_options_by_level1: {},
  facets: {},
})
const exerciseList = ref<ExerciseListResponse>({
  items: [],
  total: 0,
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_pages: 0,
})
const selectedListItem = ref<ExerciseListItem | null>(null)
const selectedDetail = ref<ExerciseLibraryItem | null>(null)
const layoutRef = ref<HTMLElement | null>(null)
const layoutHeight = ref<number | null>(null)
const showCategoryManager = ref(false)

const listLoading = ref(false)
const detailLoading = ref(false)
const metadataLoading = ref(false)
const listError = ref('')
const metadataError = ref('')
let listRequestId = 0
let detailRequestId = 0

const filters = reactive({
  keyword: '',
  level1: '',
  level2: '',
  visibility: 'all' as 'all' | 'public' | 'private',
  tags: Object.fromEntries(EXERCISE_TAG_FACETS.map(({ key }) => [key, [] as string[]])),
})

const debouncedKeyword = ref('')
let keywordDebounceTimer: number | null = null

const level1Options = computed(() => exerciseFacets.value.level1_options || [])
const level2Options = computed(() => {
  if (!filters.level1) return exerciseFacets.value.level2_options || []
  return exerciseFacets.value.level2_options_by_level1?.[filters.level1] || []
})
const facetOptions = computed(() => exerciseFacets.value.facets || {})
const isAdmin = computed(() => authStore.isAdmin)
const currentUserId = computed(() => authStore.currentUser?.id || null)
const hasTagFilters = computed(() => Object.values(filters.tags).some((values) => values.length > 0))
const listItems = computed(() => exerciseList.value.items || [])
const hasActiveFilters = computed(() =>
  Boolean(debouncedKeyword.value || filters.level1 || filters.level2 || filters.visibility !== 'all' || hasTagFilters.value),
)
const selectedDetailReadOnly = computed(() => {
  if (!selectedDetail.value?.id) return false
  if (isAdmin.value) return false
  return selectedDetail.value.visibility !== 'private' || selectedDetail.value.owner_user_id !== currentUserId.value
})
const paginationSummary = computed(() => {
  if (!exerciseList.value.total) return '当前没有动作'
  const start = (exerciseList.value.page - 1) * exerciseList.value.page_size + 1
  const end = Math.min(exerciseList.value.page * exerciseList.value.page_size, exerciseList.value.total)
  return `显示 ${start}-${end} / ${exerciseList.value.total}`
})
const selectedExerciseId = computed(() => selectedListItem.value?.id || selectedDetail.value?.id || null)

function buildListQuery(page = exerciseList.value.page || 1) {
  const tagQuery = Object.fromEntries(
    Object.entries(filters.tags)
      .map(([key, values]) => [key, values.filter(Boolean)])
      .filter(([, values]) => values.length),
  )

  return {
    keyword: debouncedKeyword.value || undefined,
    level1: filters.level1 || undefined,
    level2: filters.level2 || undefined,
    visibility: filters.visibility,
    page,
    page_size: DEFAULT_PAGE_SIZE,
    ...tagQuery,
  }
}

function logExerciseListPerformance(response: ExerciseListResponse, startedAt: number) {
  if (!import.meta.env.DEV) return
  const durationMs = Math.round(performance.now() - startedAt)
  console.info('[exercise-library] /exercises list loaded', {
    total: response.total,
    page: response.page,
    pageSize: response.page_size,
    itemCount: response.items.length,
    durationMs,
  })
}

async function loadExerciseList(page = 1, preferredId?: number | null) {
  const requestId = ++listRequestId
  listLoading.value = true
  listError.value = ''
  const startedAt = performance.now()
  try {
    const response = await fetchExercises(buildListQuery(page))
    if (requestId !== listRequestId) return
    exerciseList.value = response
    logExerciseListPerformance(response, startedAt)

    if (preferredId) {
      const matched = response.items.find((item) => item.id === preferredId) || null
      if (matched) {
        selectedListItem.value = matched
        return
      }
    }

    if (selectedExerciseId.value) {
      const matched = response.items.find((item) => item.id === selectedExerciseId.value) || null
      if (matched) {
        selectedListItem.value = matched
        return
      }
    }

    selectedListItem.value = response.items[0] || null
    if (!selectedListItem.value && !isAdmin.value) {
      selectedDetail.value = null
    }
  } catch (error: any) {
    if (requestId !== listRequestId) return
    listError.value = error?.response?.data?.detail || '动作列表加载失败，请稍后重试。'
  } finally {
    if (requestId !== listRequestId) return
    listLoading.value = false
  }
}

async function loadExerciseDetail(exerciseId: number) {
  const requestId = ++detailRequestId
  detailLoading.value = true
  try {
    const detail = await fetchExercise(exerciseId)
    if (requestId !== detailRequestId) return
    selectedDetail.value = detail
  } catch (error: any) {
    if (requestId !== detailRequestId) return
    selectedDetail.value = null
    const detail = error?.response?.data?.detail
    window.alert(typeof detail === 'string' ? detail : '动作详情加载失败，请稍后再试。')
  } finally {
    if (requestId !== detailRequestId) return
    detailLoading.value = false
  }
}

async function loadMetadata() {
  metadataLoading.value = true
  metadataError.value = ''
  try {
    const [categoryData, facetData] = await Promise.all([
      fetchExerciseCategoriesTree(),
      fetchExerciseFacets(),
    ])
    categoryTree.value = categoryData
    exerciseFacets.value = facetData
  } catch (error: any) {
    metadataError.value = error?.response?.data?.detail || '分类和标签筛选数据加载失败，稍后可重试。'
  } finally {
    metadataLoading.value = false
  }
}

async function refreshCategoryMetadata() {
  await loadMetadata()
}

async function refreshCurrentPage(preferredId?: number | null) {
  const currentPage = exerciseList.value.page || 1
  await loadExerciseList(currentPage, preferredId)
}

async function handleSave(payload: Record<string, unknown>) {
  if (selectedDetailReadOnly.value) return

  if (selectedDetail.value?.id) {
    const updated = await updateExercise(selectedDetail.value.id, payload)
    selectedDetail.value = updated
    await refreshCurrentPage(updated.id)
    return
  }

  const created = await createExercise(payload)
  selectedDetail.value = created
  await loadExerciseList(1, created.id)
}

async function handleDelete(exerciseId: number) {
  if (selectedDetailReadOnly.value) return
  try {
    await deleteExercise(exerciseId, { confirmed: true, actor_name: '管理端' })
    selectedDetail.value = null
    selectedListItem.value = null
    const currentPage = exerciseList.value.page || 1
    const shouldFallbackPage = currentPage > 1 && listItems.value.length <= 1
    await loadExerciseList(shouldFallbackPage ? currentPage - 1 : currentPage)
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    window.alert(typeof detail === 'string' ? detail : '删除动作失败，请稍后再试。')
  }
}

function clearFilters() {
  filters.keyword = ''
  filters.level1 = ''
  filters.level2 = ''
  filters.visibility = 'all'
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
  detailRequestId += 1
  detailLoading.value = false
  selectedListItem.value = null
  selectedDetail.value = null
}

function selectVisibilityFilter(value: 'all' | 'public' | 'private') {
  filters.visibility = value
}

function updateLayoutHeight() {
  if (!layoutRef.value || typeof window === 'undefined') return
  const top = layoutRef.value.getBoundingClientRect().top
  const available = Math.floor(window.innerHeight - top - 24)
  layoutHeight.value = available > 320 ? available : null
}

function goToPage(page: number) {
  if (page < 1) return
  if (exerciseList.value.total_pages && page > exerciseList.value.total_pages) return
  void loadExerciseList(page)
}

watch(
  () => filters.keyword,
  (value) => {
    if (keywordDebounceTimer) window.clearTimeout(keywordDebounceTimer)
    keywordDebounceTimer = window.setTimeout(() => {
      debouncedKeyword.value = value.trim()
    }, FILTER_DEBOUNCE_MS)
  },
  { immediate: true },
)

watch(
  () => [
    debouncedKeyword.value,
    filters.level1,
    filters.level2,
    filters.visibility,
    ...Object.values(filters.tags).map((values) => values.join('|')),
  ],
  () => {
    void loadExerciseList(1)
  },
)

watch(
  () => filters.level1,
  () => {
    if (filters.level2 && !level2Options.value.includes(filters.level2)) {
      filters.level2 = ''
    }
  },
)

watch(
  () => selectedListItem.value?.id,
  (exerciseId) => {
    if (!exerciseId) {
      if (!selectedDetail.value?.id) selectedDetail.value = null
      return
    }
    if (selectedDetail.value?.id === exerciseId) return
    void loadExerciseDetail(exerciseId)
  },
)

onMounted(() => {
  void loadExerciseList(1)
  void loadMetadata()
})

onMounted(() => {
  nextTick(() => updateLayoutHeight())
  window.addEventListener('resize', updateLayoutHeight)
})

onBeforeUnmount(() => {
  if (keywordDebounceTimer) window.clearTimeout(keywordDebounceTimer)
  window.removeEventListener('resize', updateLayoutHeight)
})

watch(
  () => selectedDetail.value?.id,
  () => nextTick(() => updateLayoutHeight()),
)
</script>

<template>
  <AppShell>
    <div
      ref="layoutRef"
      class="library-layout"
      :style="layoutHeight ? { '--library-layout-height': `${layoutHeight}px` } : {}"
    >
      <section class="panel filter-panel">
        <div class="toolbar">
          <div>
            <p class="eyebrow">动作库</p>
            <h3>动作库</h3>
          </div>
          <div class="toolbar-actions">
            <button class="primary-btn slim" @click="createCustomExercise">新建动作</button>
            <button
              v-if="isAdmin"
              class="secondary-btn slim"
              type="button"
              @click="showCategoryManager = !showCategoryManager"
            >
              {{ showCategoryManager ? '收起分类' : '分类管理' }}
            </button>
          </div>
        </div>

        <ExerciseCategoryManager
          v-if="isAdmin && showCategoryManager"
          :category-tree="categoryTree"
          @refreshed="refreshCategoryMetadata"
          @close="showCategoryManager = false"
        />

        <div class="stacked-filters">
          <div class="visibility-filter" role="group" aria-label="动作归属筛选">
            <button
              class="scope-tab"
              :class="{ active: filters.visibility === 'all' }"
              type="button"
              @click="selectVisibilityFilter('all')"
            >
              全部
            </button>
            <button
              class="scope-tab"
              :class="{ active: filters.visibility === 'public' }"
              type="button"
              @click="selectVisibilityFilter('public')"
            >
              公共动作
            </button>
            <button
              class="scope-tab"
              :class="{ active: filters.visibility === 'private' }"
              type="button"
              @click="selectVisibilityFilter('private')"
            >
              自建动作
            </button>
          </div>
          <div class="filter-row filter-row--search">
            <label class="field filter-control">
              <span class="field-label">关键词搜索</span>
              <input
                v-model="filters.keyword"
                class="text-input"
                placeholder="动作名称 / 英文名 / 分类"
              />
            </label>
          </div>
          <div class="filter-row filter-row--selects">
            <label class="field filter-control">
              <span class="field-label">一级分类</span>
              <select v-model="filters.level1" class="text-input filter-select">
                <option value="">全部一级分类</option>
                <option v-for="option in level1Options" :key="option" :value="option">{{ option }}</option>
              </select>
            </label>
            <label class="field filter-control">
              <span class="field-label">二级分类</span>
              <select v-model="filters.level2" class="text-input filter-select">
                <option value="">全部二级分类</option>
                <option v-for="option in level2Options" :key="option" :value="option">{{ option }}</option>
              </select>
            </label>
          </div>
        </div>

        <div class="filter-actions">
          <span>{{ paginationSummary }}</span>
          <button class="ghost-btn slim" @click="clearFilters">清空筛选</button>
        </div>

        <div v-if="metadataError" class="inline-notice inline-notice--warning">{{ metadataError }}</div>

        <div class="facet-panel">
          <div class="facet-panel-head">
            <strong>标签筛选</strong>
            <small>{{ metadataLoading ? '加载中…' : '标签筛选已接入后端查询。' }}</small>
          </div>
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
            <h3>{{ hasActiveFilters ? '筛选结果' : '动作分页列表' }}</h3>
          </div>
          <button class="ghost-btn slim" :disabled="listLoading" @click="refreshCurrentPage(selectedExerciseId)">刷新当前页</button>
        </div>

        <div v-if="listError" class="inline-notice inline-notice--warning">{{ listError }}</div>

        <div class="list-scroll">
          <div v-if="listLoading" class="empty-state">动作列表加载中…</div>

          <template v-else>
            <button
              v-for="exercise in listItems"
              :key="exercise.id"
              class="exercise-row adaptive-card"
              :class="{ active: selectedExerciseId === exercise.id }"
              @click="selectedListItem = exercise"
            >
              <div class="row-head">
                <strong class="adaptive-card-title">{{ exercise.name }}</strong>
                <span
                  class="visibility-badge"
                  :class="exercise.visibility === 'public' ? 'visibility-badge--public' : 'visibility-badge--private'"
                >
                  {{ exercise.visibility === 'public' ? '公共动作' : (exercise.owner_name ? `${exercise.owner_name}自建` : '自建动作') }}
                </span>
              </div>
              <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ exercise.name_en || exercise.alias || '无英文名' }}</span>
              <small class="adaptive-card-meta adaptive-card-clamp-2">
                {{ exercise.category_path || `${exercise.level1_category || '未分类'} / ${exercise.level2_category || '未分类'}` }}
              </small>
              <div class="tag-line">
                <span v-for="tag in summarizeExerciseListTags(exercise)" :key="tag" class="tag-chip">{{ tag }}</span>
              </div>
            </button>
            <div v-if="!listItems.length" class="empty-state">当前筛选条件下没有动作。</div>
          </template>
        </div>

        <div class="pagination-bar">
          <button class="ghost-btn slim" :disabled="listLoading || exerciseList.page <= 1" @click="goToPage(exerciseList.page - 1)">
            上一页
          </button>
          <span>第 {{ exerciseList.page }} / {{ exerciseList.total_pages || 1 }} 页</span>
          <button
            class="ghost-btn slim"
            :disabled="listLoading || exerciseList.page >= exerciseList.total_pages"
            @click="goToPage(exerciseList.page + 1)"
          >
            下一页
          </button>
        </div>
      </section>

      <div class="editor-panel-wrap">
        <div v-if="detailLoading" class="panel loading-panel">动作详情加载中…</div>
        <ExerciseLibraryEditor
          v-else
          class="editor-panel"
          :model-value="selectedDetail"
          :category-tree="categoryTree"
          :facet-options="facetOptions"
          :read-only="selectedDetailReadOnly"
          @submit="handleSave"
          @remove="handleDelete"
        />
      </div>
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
.editor-panel-wrap,
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

.list-panel,
.editor-panel-wrap {
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.editor-panel-wrap {
  display: grid;
}

.toolbar,
.toolbar-actions,
.filter-actions,
.list-head,
.facet-group,
.facet-options,
.row-head,
.tag-line,
.pagination-bar,
.visibility-filter,
.facet-panel-head {
  display: flex;
  gap: 10px;
}

.toolbar,
.filter-actions,
.list-head,
.row-head,
.pagination-bar {
  align-items: center;
  justify-content: space-between;
}

.row-head {
  min-width: 0;
}

.row-head .adaptive-card-title {
  min-width: 0;
}

.toolbar {
  align-items: start;
}

.library-layout--readonly .toolbar-actions {
  display: none;
}

.toolbar-actions,
.facet-options,
.tag-line,
.visibility-filter {
  flex-wrap: wrap;
}

.facet-panel,
.facet-group {
  display: grid;
  gap: 10px;
}

.facet-panel--muted {
  opacity: 0.78;
}

.facet-panel-head {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.facet-group {
  padding-top: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.facet-chip,
.tag-chip,
.source-badge,
.visibility-badge,
.scope-tab {
  min-height: 32px;
  border-radius: 999px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
}

.visibility-badge {
  flex: 0 0 auto;
  min-height: 28px;
  padding: 0 10px;
  line-height: 1;
  white-space: nowrap;
}

.facet-chip,
.tag-chip {
  background: #e2e8f0;
}

.facet-chip.active {
  background: var(--primary);
  color: white;
}

.scope-tab {
  justify-content: center;
  background: #eef2f7;
  font-weight: 700;
  color: var(--text);
}

.scope-tab.active {
  background: var(--primary);
  color: white;
}

.facet-chip:disabled {
  cursor: not-allowed;
}

.source-badge {
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
}

.visibility-badge--public {
  background: rgba(20, 184, 166, 0.12);
  color: #0f766e;
}

.visibility-badge--private {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
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
  display: flex;
  flex-direction: column;
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

.empty-state,
.loading-panel,
.inline-notice {
  padding: 20px 16px;
  text-align: center;
  color: var(--muted);
  border-radius: 16px;
}

.empty-state,
.loading-panel {
  border: 1px dashed var(--line);
}

.inline-notice {
  padding: 12px 14px;
  text-align: left;
  border: 1px solid rgba(245, 158, 11, 0.28);
  background: rgba(254, 243, 199, 0.6);
  color: #92400e;
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
}
</style>
