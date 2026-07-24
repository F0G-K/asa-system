<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  visible: boolean
  title: string
  message: string
  confirmText?: string
  confirmType?: 'danger' | 'primary' | 'warning'
  requireNameInput?: boolean
  expectedName?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: '确定',
  confirmType: 'danger',
  requireNameInput: false,
  expectedName: '',
  loading: false,
})

const emit = defineEmits<{
  confirm: []
  cancel: []
  'update:visible': [value: boolean]
}>()

const nameInput = ref('')

const nameMismatch = computed(() => {
  if (!props.requireNameInput) return false
  if (!nameInput.value) return true
  return nameInput.value.trim() !== props.expectedName
})

const canConfirm = computed(() => {
  if (props.loading) return false
  if (props.requireNameInput) return !nameMismatch.value
  return true
})

function handleClose() {
  nameInput.value = ''
  emit('update:visible', false)
  emit('cancel')
}

function handleConfirm() {
  if (!canConfirm.value) return
  emit('confirm')
}

function handleOpened() {
  nameInput.value = ''
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="!loading"
    destroy-on-close
    @update:model-value="(val: boolean) => !val && handleClose()"
    @opened="handleOpened"
  >
    <div class="confirm-dialog">
      <p class="confirm-dialog__message">{{ message }}</p>

      <div v-if="requireNameInput" class="confirm-dialog__input">
        <p class="confirm-dialog__input-hint">
          请输入项目名称 <strong>{{ expectedName }}</strong> 以确认删除：
        </p>
        <el-input
          v-model="nameInput"
          placeholder="请输入项目名称"
          :disabled="loading"
        />
        <p v-if="nameInput && nameMismatch" class="confirm-dialog__input-error">
          项目名称不匹配
        </p>
      </div>
    </div>

    <template #footer>
      <div class="confirm-dialog__footer">
        <el-button :disabled="loading" @click="handleClose">
          取消
        </el-button>
        <el-button
          :type="confirmType"
          :loading="loading"
          :disabled="!canConfirm"
          @click="handleConfirm"
        >
          {{ confirmText }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.confirm-dialog__message {
  font-size: var(--font-size-base);
  color: var(--color-text-regular);
  line-height: 1.6;
}

.confirm-dialog__input {
  margin-top: var(--spacing-lg);
}

.confirm-dialog__input-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
}

.confirm-dialog__input-error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
  margin-top: var(--spacing-xs);
}

.confirm-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}
</style>
