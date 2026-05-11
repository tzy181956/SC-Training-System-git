export type ExerciseSourceType = 'exos_excel' | 'custom_manual'

export interface ExerciseCategoryNode {
  id: number
  parent_id: number | null
  level: number
  name_zh: string
  name_en?: string | null
  code: string
  sort_order: number
  is_system: boolean
  children?: ExerciseCategoryNode[]
}

export interface ExerciseBaseCategoryRef {
  id: number
  level: number
  name_zh: string
  name_en?: string | null
  code: string
}

export interface ExerciseTagMap {
  functionType?: string[]
  trainingGoal?: string[]
  bodyRegion?: string[]
  subBodyPart?: string[]
  primaryPattern?: string[]
  secondaryPattern?: string[]
  direction?: string[]
  lowerDominance?: string[]
  limbCombination?: string[]
  laterality?: string[]
  powerType?: string[]
  equipment?: string[]
  bodyPosition?: string[]
  usageScene?: string[]
  fmsItem?: string[]
  fmsPhase?: string[]
  fmsLevel?: string[]
  [key: string]: string[] | undefined
}

export interface ExerciseLibraryItem {
  id: number
  name: string
  alias?: string | null
  code?: string | null
  source_type: ExerciseSourceType
  name_en?: string | null
  level1_category?: string | null
  level2_category?: string | null
  base_movement?: string | null
  category_path?: string | null
  original_english_fields?: Record<string, string | null> | null
  structured_tags?: ExerciseTagMap | null
  search_keywords?: string[] | null
  tag_text?: string | null
  raw_row?: Record<string, string> | null
  base_category_id?: number | null
  base_category?: ExerciseBaseCategoryRef | null
  description?: string | null
  video_url?: string | null
  video_path?: string | null
  coaching_points?: string | null
  common_errors?: string | null
  notes?: string | null
  default_increment?: number | null
  is_main_lift_candidate: boolean
}

export interface ExerciseListItem {
  id: number
  name: string
  alias?: string | null
  code?: string | null
  source_type: ExerciseSourceType
  name_en?: string | null
  level1_category?: string | null
  level2_category?: string | null
  base_movement?: string | null
  category_path?: string | null
  base_category_id?: number | null
  is_main_lift_candidate: boolean
  tag_summary: string[]
}

export interface ExerciseListResponse {
  items: ExerciseListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ExerciseImportPreview {
  source_path: string
  total_rows: number
  valid_rows: number
  unique_codes: number
  level1_categories: number
  level2_categories: number
  level3_categories: number
  exercises: number
  to_create: number
  to_update: number
  skipped_duplicates: number
}

export interface ExerciseLibraryFilters {
  keyword: string
  level1: string
  level2: string
  tags: Record<string, string[]>
}

export interface ExerciseFacetValues {
  level1_options: string[]
  level2_options: string[]
  level2_options_by_level1: Record<string, string[]>
  facets: Record<string, string[]>
}
