<script setup lang="ts">
import { ref, PropType, toRaw, onMounted } from 'vue'
import { Metadata } from '@/components/types'

const props = defineProps({
  meta: {
    type: Object as PropType<Metadata>,
    required: true
  },
  api: {
    type: Object,
    required: true
  },
  endpoint: {
    type: String,
    required: true
  },
  region: String,
  presetIdentifiers: {
    type: Array as PropType<string[]>,
    required: true
  }
})
const emit = defineEmits<{
  (e: 'refresh', regions: string[]): void
  (e: 'show-snackbar', value: any): void
  (e: 'show-error', msg: string): void
  (e: 'close'): void
}>()

const loading = ref(false)
const invisibleTo = ref<string[]>(structuredClone(toRaw(props.meta?.invisible_to) || []))

// New state
const selectedPresets = ref<string[]>([])
const customExpressions = ref<string[]>([])
const expressionTemplate = (id: string) => `identifier == '${id}'`
const expressionRegex = /^identifier == '(.+)'$/

onMounted(() => {
  parseInvisibleTo()
})

function parseInvisibleTo() {
  const presets: string[] = []
  const custom: string[] = []
  const currentInvisible = invisibleTo.value || []

  currentInvisible.forEach((expr) => {
    const match = expr.match(expressionRegex)
    if (match && props.presetIdentifiers.includes(match[1])) {
      presets.push(match[1])
    } else {
      custom.push(expr)
    }
  })

  selectedPresets.value = presets
  customExpressions.value = custom
}

function addCustomExpression() {
  customExpressions.value.push('')
}

function removeCustomExpression(index: number) {
  customExpressions.value.splice(index, 1)
}

async function updateDataVisibility() {
  // Sync state to invisibleTo
  let newInvisibleTo: string[]
  newInvisibleTo = [
    ...selectedPresets.value.map((id) => expressionTemplate(id)),
    ...customExpressions.value.filter((e) => e.trim() !== '')
  ]
  invisibleTo.value = newInvisibleTo

  loading.value = true
  try {
    const meta: Metadata = structuredClone(toRaw(props.meta))
    meta.invisible_to = invisibleTo.value
    // Send full metadata with updated invisible_to
    const result = await props.api.patch(props.endpoint, meta)
    if (props.region) emit('refresh', [props.region])
    if (result?.success) {
      emit('show-snackbar', {
        show: true,
        message: '可见性配置更新成功',
        color: 'success'
      })
      emit('close')
    } else {
      emit('show-error', '更新可见性配置失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '更新可见性配置失败',
        color: 'error'
      })
    }
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', err.message || '更新可见性配置失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-dialog max-width="40rem">
    <v-card>
      <v-card-title> 限制可见性 </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4" density="compact">
          配置数据项对哪些设备不可见。勾选预设设备或输入自定义表达式 (simpleeval)。
        </v-alert>

        <div class="text-subtitle-1 mb-2">预设设备</div>
        <v-chip-group
          v-model="selectedPresets"
          column
          multiple
          filter
          selected-class="text-primary"
        >
          <v-chip v-for="id in presetIdentifiers" :key="id" :value="id" variant="outlined" filter>
            {{ id }}
          </v-chip>
        </v-chip-group>

        <v-divider class="my-4"></v-divider>

        <div class="d-flex align-center justify-space-between mb-2">
          <div class="text-subtitle-1">自定义表达式</div>
          <v-btn
            size="small"
            variant="text"
            color="primary"
            prepend-icon="mdi-plus"
            @click="addCustomExpression"
          >
            添加
          </v-btn>
        </div>

        <div
          v-for="index in customExpressions.keys()"
          :key="index"
          class="d-flex align-center mb-2"
        >
          <v-text-field
            v-model="customExpressions[index]"
            label="表达式"
            variant="outlined"
            density="compact"
            hide-details
            class="flex-grow-1"
          ></v-text-field>
          <v-btn
            icon="mdi-delete"
            variant="text"
            color="error"
            size="small"
            class="ml-2"
            @click="removeCustomExpression(index)"
          ></v-btn>
        </div>
        <div v-if="customExpressions.length === 0" class="text-caption text-grey text-center py-2">
          无自定义表达式
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="secondary" @click="$emit('close')">取消</v-btn>
        <v-btn color="primary" :loading="loading" @click="updateDataVisibility">保存</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
