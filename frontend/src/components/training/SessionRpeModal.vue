<script setup lang="ts">
import { computed, ref, watch, type CSSProperties } from 'vue'

import {
  getSessionRpeColorTheme,
  getSessionRpeHelp,
  getSessionRpeLabel,
  SESSION_RPE_VALUES,
} from '@/constants/sessionRpe'

const props = defineProps<{
  open: boolean
  initialRpe?: number | null
  initialFeedback?: string | null
  submitting?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  closeLater: []
  submit: [payload: { session_rpe: number; session_feedback: string | null }]
}>()

const selectedRpe = ref<number | null>(null)
const feedbackText = ref('')
const manualInputOpen = ref(false)
const manualInputValue = ref('')

const hasSelectedRpe = computed(() => selectedRpe.value !== null)
const sliderValue = computed(() => selectedRpe.value ?? 0)
const selectedTheme = computed(() => getSessionRpeColorTheme(selectedRpe.value))
const selectedLabel = computed(() => getSessionRpeLabel(selectedRpe.value, '请选择 RPE'))
const selectedHelp = computed(() => getSessionRpeHelp(selectedRpe.value, '选择本次训练的整体主观用力程度'))
const selectedScoreText = computed(() => (selectedRpe.value == null ? 'RPE --/10' : `RPE ${selectedRpe.value}/10`))
const themeStyle = computed<CSSProperties>(() => ({
  '--session-rpe-accent': selectedTheme.value.accent,
  '--session-rpe-accent-soft': selectedTheme.value.softBackground,
  '--session-rpe-accent-border': selectedTheme.value.border,
  '--session-rpe-accent-surface': selectedTheme.value.surface,
  '--session-rpe-accent-shadow': selectedTheme.value.shadow,
}))
const feedbackTooLong = computed(() => feedbackText.value.trim().length > 500)
const feedbackLength = computed(() => feedbackText.value.trim().length)
const manualInputError = computed(() => {
  if (!manualInputValue.value.trim()) return '请输入 0-10 的整数'
  if (!/^(10|[0-9])$/.test(manualInputValue.value.trim())) return '请输入 0-10 的整数'
  return ''
})
const canConfirmManualInput = computed(() => manualInputError.value === '')
const canSubmit = computed(() => hasSelectedRpe.value && !feedbackTooLong.value && !props.submitting)

watch(
  () => props.open,
  (open) => {
    if (!open) return
    selectedRpe.value = props.initialRpe ?? null
    feedbackText.value = props.initialFeedback ?? ''
    manualInputOpen.value = false
    manualInputValue.value = props.initialRpe == null ? '' : String(props.initialRpe)
  },
  { immediate: true },
)

function chooseRpe(value: number) {
  selectedRpe.value = value
  manualInputValue.value = String(value)
}

function handleSliderInput(event: Event) {
  const nextValue = Number((event.target as HTMLInputElement).value)
  chooseRpe(nextValue)
}

function openManualInput() {
  manualInputOpen.value = true
  manualInputValue.value = selectedRpe.value == null ? '' : String(selectedRpe.value)
}

function cancelManualInput() {
  manualInputOpen.value = false
  manualInputValue.value = selectedRpe.value == null ? '' : String(selectedRpe.value)
}

function confirmManualInput() {
  if (!canConfirmManualInput.value) return
  chooseRpe(Number(manualInputValue.value.trim()))
  manualInputOpen.value = false
}

function submitFeedback() {
  if (!canSubmit.value || selectedRpe.value === null) return
  emit('submit', {
    session_rpe: selectedRpe.value,
    session_feedback: feedbackText.value.trim() ? feedbackText.value.trim() : null,
  })
}
</script>

<template>
  <div v-if="open" class="session-rpe-modal-overlay" role="presentation">
    <article
      class="session-rpe-modal"
      :style="themeStyle"
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-rpe-title"
      @click.stop
    >
      <header class="modal-head">
        <div>
          <p class="modal-eyebrow">训练反馈</p>
          <h2 id="session-rpe-title">今日训练已完成</h2>
          <p class="modal-description">请评价本次训练整体强度</p>
        </div>
      </header>

      <section class="rpe-display-panel">
        <span class="rpe-score-chip" :class="{ empty: !hasSelectedRpe }">{{ selectedScoreText }}</span>
        <strong class="rpe-headline" :class="{ empty: !hasSelectedRpe }">{{ selectedLabel }}</strong>
        <p class="rpe-help" :class="{ empty: !hasSelectedRpe }">{{ selectedHelp }}</p>
        <button class="secondary-btn manual-trigger" type="button" @click="openManualInput">手动输入</button>
      </section>

      <section v-if="manualInputOpen" class="manual-input-panel">
        <label class="field">
          <span>输入 0-10 的整数</span>
          <input
            v-model="manualInputValue"
            class="text-input manual-input"
            type="text"
            inputmode="numeric"
            placeholder="例如 7"
          />
        </label>
        <p v-if="manualInputError" class="field-error">{{ manualInputError }}</p>
        <div class="manual-input-actions">
          <button class="secondary-btn modal-btn" type="button" @click="cancelManualInput">取消</button>
          <button class="primary-btn modal-btn" type="button" :disabled="!canConfirmManualInput" @click="confirmManualInput">
            确定
          </button>
        </div>
      </section>

      <section class="slider-panel">
        <input
          class="rpe-slider"
          type="range"
          min="0"
          max="10"
          step="1"
          :value="sliderValue"
          @input="handleSliderInput"
        />
        <div class="scale-row">
          <button
            v-for="value in SESSION_RPE_VALUES"
            :key="value"
            class="scale-button"
            :class="{ active: selectedRpe === value }"
            type="button"
            @click="chooseRpe(value)"
          >
            {{ value }}
          </button>
        </div>
        <p v-if="!hasSelectedRpe" class="selection-hint">请先选择本次训练整体 RPE</p>
      </section>

      <section class="feedback-panel">
        <label class="field">
          <span>今日感受备注，可选</span>
          <textarea
            v-model="feedbackText"
            class="text-input feedback-textarea"
            rows="4"
            placeholder="例如：腿部疲劳明显、状态不错、膝盖不舒服"
          />
        </label>
        <div class="feedback-meta">
          <span :class="{ error: feedbackTooLong }">{{ feedbackLength }} / 500</span>
          <span v-if="feedbackTooLong" class="field-error">备注不能超过 500 字</span>
        </div>
      </section>

      <p v-if="error" class="submit-error">{{ error }}</p>

      <footer class="modal-actions">
        <button class="secondary-btn modal-btn" type="button" :disabled="props.submitting" @click="emit('closeLater')">
          稍后填写
        </button>
        <button class="primary-btn modal-btn submit-btn" type="button" :disabled="!canSubmit" @click="submitFeedback">
          {{ props.submitting ? '提交中...' : '提交并结束训练' }}
        </button>
      </footer>
    </article>
  </div>
</template>

<style scoped>
.session-rpe-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.46);
}

.session-rpe-modal {
  --session-rpe-accent: #94a3b8;
  --session-rpe-accent-soft: rgba(148, 163, 184, 0.14);
  --session-rpe-accent-border: rgba(148, 163, 184, 0.28);
  --session-rpe-accent-surface: rgba(148, 163, 184, 0.06);
  --session-rpe-accent-shadow: rgba(148, 163, 184, 0.12);
  width: min(760px, calc(100vw - 32px));
  max-height: calc(100dvh - 48px);
  overflow-y: auto;
  display: grid;
  gap: 18px;
  padding: 24px;
  border-radius: 24px;
  background: white;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.32);
}

.modal-head,
.rpe-display-panel,
.manual-input-panel,
.slider-panel,
.feedback-panel {
  display: grid;
  gap: 10px;
}

.modal-eyebrow,
.modal-description,
.field span,
.feedback-meta span {
  margin: 0;
  color: var(--text-soft);
}

.modal-head h2 {
  margin: 0;
  font-size: clamp(1.7rem, 2.4vw, 2.25rem);
  line-height: 1.08;
}

.rpe-display-panel {
  justify-items: center;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid var(--session-rpe-accent-border);
  background: linear-gradient(180deg, var(--session-rpe-accent-surface), rgba(248, 250, 252, 0.9));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
  text-align: center;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease;
}

.rpe-score-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--session-rpe-accent-border);
  background: var(--session-rpe-accent-soft);
  color: var(--session-rpe-accent);
  font-size: 0.95rem;
  line-height: 1.1;
  font-weight: 700;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;
}

.rpe-score-chip.empty {
  border-color: rgba(148, 163, 184, 0.24);
  background: rgba(148, 163, 184, 0.08);
  color: var(--text-soft);
}

.rpe-headline {
  max-width: 100%;
  font-size: clamp(2.25rem, 4.8vw, 3.4rem);
  line-height: 1.08;
  font-weight: 900;
  color: var(--session-rpe-accent);
  text-align: center;
  text-shadow: 0 10px 24px var(--session-rpe-accent-shadow);
  transition: color 0.2s ease, text-shadow 0.2s ease;
}

.rpe-headline.empty {
  color: var(--text);
  text-shadow: none;
}

.rpe-help {
  max-width: 520px;
  margin: 0;
  color: var(--text-soft);
  font-size: 1rem;
  line-height: 1.45;
}

.rpe-help.empty {
  color: var(--text-soft);
}

.manual-trigger {
  min-height: 44px;
}

.manual-input-panel {
  padding: 14px;
  border: 1px solid rgba(14, 165, 233, 0.22);
  border-radius: 16px;
  background: rgba(239, 246, 255, 0.7);
}

.manual-input {
  min-height: 48px;
  font-size: 18px;
}

.manual-input-actions,
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.rpe-slider {
  width: 100%;
  min-height: 44px;
  accent-color: var(--session-rpe-accent);
  transition: accent-color 0.2s ease;
}

.rpe-slider::-webkit-slider-thumb {
  box-shadow: 0 0 0 5px var(--session-rpe-accent-soft);
}

.rpe-slider::-moz-range-thumb {
  box-shadow: 0 0 0 5px var(--session-rpe-accent-soft);
}

.scale-row {
  display: grid;
  grid-template-columns: repeat(11, minmax(0, 1fr));
  gap: 8px;
}

.scale-button {
  min-height: 40px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #f8fafc;
  color: var(--text);
  font-size: 1rem;
  font-weight: 700;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease;
}

.scale-button.active {
  border-color: var(--session-rpe-accent-border);
  background: var(--session-rpe-accent-soft);
  color: var(--session-rpe-accent);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.72),
    0 6px 16px -10px var(--session-rpe-accent-shadow);
}

.selection-hint,
.field-error,
.submit-error {
  margin: 0;
  font-size: 0.95rem;
}

.selection-hint {
  color: #92400e;
}

.field-error,
.submit-error,
.feedback-meta span.error {
  color: #b91c1c;
}

.field {
  display: grid;
  gap: 8px;
}

.feedback-textarea {
  min-height: 116px;
  font-size: 18px;
  resize: vertical;
}

.feedback-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.modal-btn {
  min-height: 48px;
  min-width: 132px;
}

.submit-btn:disabled {
  cursor: not-allowed;
}

@media (max-width: 767px) {
  .session-rpe-modal-overlay {
    padding: 12px;
  }

  .session-rpe-modal {
    width: calc(100vw - 24px);
    max-height: calc(100dvh - 24px);
    padding: 18px;
    border-radius: 20px;
  }

  .scale-row {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .modal-actions,
  .manual-input-actions {
    justify-content: stretch;
  }

  .modal-btn {
    flex: 1 1 180px;
  }
}
</style>
