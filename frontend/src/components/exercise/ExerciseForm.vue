<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  modelValue?: Record<string, any> | null
  tags: any[]
}>()

const emit = defineEmits<{ submit: [payload: Record<string, unknown>] }>()

function normalizeSingleLineText(value: unknown) {
  return String(value || '')
    .replace(/\r?\n+/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

const form = reactive({
  name: '',
  alias: '',
  description: '',
  video_url: '',
  coaching_points: '',
  common_errors: '',
  notes: '',
  default_increment: 2.5,
  is_main_lift_candidate: false,
  tag_ids: [] as number[],
})

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      Object.assign(form, {
        name: '',
        alias: '',
        description: '',
        video_url: '',
        coaching_points: '',
        common_errors: '',
        notes: '',
        default_increment: 2.5,
        is_main_lift_candidate: false,
        tag_ids: [],
      })
      return
    }
    Object.assign(form, {
      ...form,
      ...value,
      name: normalizeSingleLineText(value.name || ''),
      alias: normalizeSingleLineText(value.alias || ''),
      description: normalizeSingleLineText(value.description || ''),
      video_url: normalizeSingleLineText(value.video_url || ''),
      coaching_points: normalizeSingleLineText(value.coaching_points || ''),
      common_errors: normalizeSingleLineText(value.common_errors || ''),
      notes: normalizeSingleLineText(value.notes || ''),
      tag_ids: (value.tags || []).map((tag: any) => tag.id ?? tag.tag?.id),
    })
  },
  { immediate: true },
)

function handleSubmit() {
  emit('submit', {
    ...form,
    name: normalizeSingleLineText(form.name),
    alias: normalizeSingleLineText(form.alias) || null,
    description: normalizeSingleLineText(form.description) || null,
    video_url: normalizeSingleLineText(form.video_url) || null,
    coaching_points: normalizeSingleLineText(form.coaching_points) || null,
    common_errors: normalizeSingleLineText(form.common_errors) || null,
    notes: normalizeSingleLineText(form.notes) || null,
  })
}
</script>

<template>
  <div class="panel form-grid">
    <label class="field">
      <span class="field-label">动作名称 <strong class="required-mark">*</strong></span>
      <input v-model="form.name" class="text-input" placeholder="必填" />
    </label>

    <label class="field">
      <span class="field-label">别名</span>
      <input v-model="form.alias" class="text-input" placeholder="可选" />
    </label>

    <label class="field">
      <span class="field-label">默认步长</span>
      <input v-model.number="form.default_increment" type="number" class="text-input" placeholder="可选" />
    </label>

    <label class="field">
      <span class="field-label">视频链接</span>
      <input v-model="form.video_url" class="text-input" placeholder="可选" />
    </label>

    <label class="field">
      <span class="field-label">动作描述</span>
      <input v-model="form.description" class="text-input" placeholder="可选" />
    </label>

    <label class="field">
      <span class="field-label">技术要点</span>
      <input v-model="form.coaching_points" class="text-input" placeholder="可选" />
    </label>

    <label class="field">
      <span class="field-label">常见错误</span>
      <input v-model="form.common_errors" class="text-input" placeholder="可选" />
    </label>

    <label class="field">
      <span class="field-label">备注</span>
      <input v-model="form.notes" class="text-input" placeholder="可选" />
    </label>

    <div class="tag-grid">
      <button
        v-for="tag in tags"
        :key="tag.id"
        class="tag-btn"
        :class="{ active: form.tag_ids.includes(tag.id) }"
        type="button"
        @click="form.tag_ids = form.tag_ids.includes(tag.id) ? form.tag_ids.filter((id) => id !== tag.id) : [...form.tag_ids, tag.id]"
      >
        {{ tag.name }}
      </button>
    </div>

    <button class="primary-btn" @click="handleSubmit">保存动作</button>
  </div>
</template>

<style scoped>
.form-grid {
  display: grid;
  gap: 12px;
  height: 100%;
  min-height: 0;
  align-content: start;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.field {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 13px;
  color: var(--text-soft);
}

.required-mark {
  color: #dc2626;
  font-weight: 700;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-btn {
  min-height: 44px;
  border-radius: 999px;
  padding: 0 14px;
  background: #e2e8f0;
}

.tag-btn.active {
  background: var(--primary);
  color: white;
}
</style>
