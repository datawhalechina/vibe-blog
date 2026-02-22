<script setup lang="ts">
import { Minus, Plus } from 'lucide-vue-next'
import { useFontScale } from '@/composables/useFontScale'

const {
  fontScale,
  formattedScale,
  setFontScale,
  stepUp,
  stepDown,
  reset,
  isDefault,
  canStepUp,
  canStepDown,
} = useFontScale()

function onSliderInput(e: Event) {
  const target = e.target as HTMLInputElement
  setFontScale(parseFloat(target.value))
}
</script>

<template>
  <div class="font-size-control">
    <button
      class="font-size-control__btn"
      :disabled="!canStepDown"
      aria-label="Decrease font size"
      @click="stepDown"
    >
      <Minus :size="14" />
    </button>

    <input
      type="range"
      class="font-size-control__slider"
      :min="0.8"
      :max="1.5"
      :step="0.05"
      :value="fontScale"
      aria-label="Font scale"
      @input="onSliderInput"
    />

    <button
      class="font-size-control__btn"
      :disabled="!canStepUp"
      aria-label="Increase font size"
      @click="stepUp"
    >
      <Plus :size="14" />
    </button>

    <span class="font-size-control__label">{{ formattedScale }}</span>

    <button
      v-if="!isDefault"
      class="font-size-control__reset"
      aria-label="Reset font size"
      @click="reset"
    >
      Reset
    </button>
  </div>
</template>

<style scoped>
.font-size-control {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.font-size-control__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-background);
  color: var(--color-foreground);
  cursor: pointer;
  transition: var(--transition-fast);
}

.font-size-control__btn:hover:not(:disabled) {
  background: var(--color-bg-hover);
  border-color: var(--color-border-hover);
}

.font-size-control__btn:disabled {
  opacity: var(--opacity-disabled);
  cursor: not-allowed;
}

.font-size-control__slider {
  width: 80px;
  accent-color: var(--color-primary);
}

.font-size-control__label {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  min-width: 36px;
  text-align: center;
}

.font-size-control__reset {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.font-size-control__reset:hover {
  background: var(--color-primary-light);
}
</style>
