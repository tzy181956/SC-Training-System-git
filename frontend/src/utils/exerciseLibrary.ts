import type {
  ExerciseCategoryNode,
  ExerciseLibraryFilters,
  ExerciseListItem,
  ExerciseLibraryItem,
} from '@/types/exerciseLibrary'

export const EXERCISE_TAG_FACETS = [
  { key: 'bodyRegion', label: '动作区域' },
  { key: 'primaryPattern', label: '主动作模式' },
  { key: 'secondaryPattern', label: '动作模式补充' },
  { key: 'direction', label: '方向属性' },
  { key: 'lowerDominance', label: '下肢主导' },
  { key: 'limbCombination', label: '肢体组合' },
  { key: 'laterality', label: '侧别' },
  { key: 'powerType', label: '动力属性' },
  { key: 'equipment', label: '器械' },
  { key: 'bodyPosition', label: '体位' },
  { key: 'usageScene', label: '应用场景' },
  { key: 'trainingGoal', label: '训练目标' },
  { key: 'functionType', label: '功能类型' },
] as const

export const EXERCISE_DETAIL_FACETS = [
  ...EXERCISE_TAG_FACETS,
  { key: 'subBodyPart', label: '细分部位' },
  { key: 'fmsItem', label: 'FMS项目' },
  { key: 'fmsPhase', label: 'FMS阶段' },
  { key: 'fmsLevel', label: 'FMS等级' },
] as const

export function normalizeString(value: unknown) {
  return String(value || '').trim()
}

export function flattenCategoryTree(nodes: ExerciseCategoryNode[]) {
  const flattened: ExerciseCategoryNode[] = []
  const walk = (items: ExerciseCategoryNode[]) => {
    items.forEach((item) => {
      flattened.push(item)
      if (item.children?.length) walk(item.children)
    })
  }
  walk(nodes)
  return flattened
}

export function filterExerciseLibrary(items: ExerciseLibraryItem[], filters: ExerciseLibraryFilters) {
  const keyword = filters.keyword.trim().toLowerCase()
  return items.filter((item) => {
    if (filters.level1 && item.level1_category !== filters.level1) return false
    if (filters.level2 && item.level2_category !== filters.level2) return false

    if (keyword) {
      const blob = [
        item.name,
        item.name_en,
        ...(item.search_keywords || []),
        item.tag_text,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      if (!blob.includes(keyword)) return false
    }

    for (const [key, selected] of Object.entries(filters.tags)) {
      if (!selected.length) continue
      const values = item.structured_tags?.[key] || []
      if (!selected.some((option) => values.includes(option))) return false
    }
    return true
  })
}

export function buildExerciseLibraryFacets(items: ExerciseLibraryItem[]) {
  return Object.fromEntries(
    EXERCISE_TAG_FACETS.map(({ key }) => {
      const values = Array.from(
        new Set(
          items.flatMap((item) => item.structured_tags?.[key] || []).filter(Boolean),
        ),
      ).sort((left, right) => left.localeCompare(right, 'zh-CN'))
      return [key, values]
    }),
  ) as Record<string, string[]>
}

export function getLevel1Options(items: ExerciseLibraryItem[]) {
  return Array.from(new Set(items.map((item) => normalizeString(item.level1_category)).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right, 'zh-CN'),
  )
}

export function getLevel2Options(items: ExerciseLibraryItem[], level1: string) {
  return Array.from(
    new Set(
      items
        .filter((item) => !level1 || item.level1_category === level1)
        .map((item) => normalizeString(item.level2_category))
        .filter(Boolean),
    ),
  ).sort((left, right) => left.localeCompare(right, 'zh-CN'))
}

export function summarizeExerciseTags(item: Pick<ExerciseLibraryItem, 'structured_tags'>, limit = 4) {
  const values = EXERCISE_TAG_FACETS.flatMap(({ key }) => item.structured_tags?.[key] || []).filter(Boolean)
  return Array.from(new Set(values)).slice(0, limit)
}

export function summarizeExerciseListTags(item: Pick<ExerciseListItem, 'tag_summary'>, limit = 4) {
  return Array.from(new Set((item.tag_summary || []).filter(Boolean))).slice(0, limit)
}

export function buildCategoryPathLabel(category: Pick<ExerciseCategoryNode, 'name_zh'>[], fallback = '未分类') {
  const parts = category.map((item) => normalizeString(item.name_zh)).filter(Boolean)
  return parts.length ? parts.join(' / ') : fallback
}

export function buildExerciseOptionLabel(item: Pick<ExerciseLibraryItem, 'name' | 'base_movement' | 'level2_category'>) {
  const extras = [normalizeString(item.base_movement), normalizeString(item.level2_category)].filter(Boolean)
  return extras.length ? `${item.name}｜${extras.join('｜')}` : item.name
}
