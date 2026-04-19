<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  modelValue?: Record<string, any> | null
  tags: any[]
}>()

const emit = defineEmits<{ submit: [payload: Record<string, unknown>] }>()

const form = reactive({
  name: '',
  alias: '',
  description: '',
  video_url: '',
  coaching_points: '',
  common_errors: '',
  notes: '',
  load_profile: 'general',
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
        load_profile: 'general',
        default_increment: 2.5,
        is_main_lift_candidate: false,
        tag_ids: [],
      })
      return
    }
    Object.assign(form, {
      ...form,
      ...value,
      tag_ids: (value.tags || []).map((tag: any) => tag.id ?? tag.tag?.id),
    })
  },
  { immediate: true },
)

function handleSubmit() {
  emit('submit', { ...form })
}
</script>

<template>
  <div class="panel form-grid">
    <input v-model="form.name" class="text-input" placeholder="动作名称" />
    <input v-model="form.alias" class="text-input" placeholder="别名" />
    <select v-model="form.load_profile" class="text-input">
      <option value="general">通用</option>
      <option value="push">推类</option>
      <option value="squat">深蹲类</option>
      <option value="pull">拉类</option>
    </select>
    <input v-model.number="form.default_increment" type="number" class="text-input" placeholder="默认步长" />
    <input v-model="form.video_url" class="text-input" placeholder="视频链接" />
    <textarea v-model="form.description" class="text-input area" placeholder="动作描述" />
    <textarea v-model="form.coaching_points" class="text-input area" placeholder="技术要点" />
    <textarea v-model="form.common_errors" class="text-input area" placeholder="常见错误" />
    <textarea v-model="form.notes" class="text-input area" placeholder="备注" />
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
