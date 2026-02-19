<script setup lang="ts">
import { ref } from 'vue'
import { VAceEditor } from 'vue3-ace-editor'
import 'ace-builds/src-noconflict/ace'
import 'ace-builds/src-noconflict/mode-yaml'
import 'ace-builds/src-noconflict/theme-monokai'

const props = defineProps<{
  modelValue: boolean
  api: any
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh'): void
  (e: 'show-snackbar', value: any): void
  (e: 'show-error', msg: string): void
}>()

const editorOptions = {
  enableBasicAutocompletion: true,
  enableSnippets: true,
  enableLiveAutocompletion: true,
  showLineNumbers: true,
  tabSize: 2
}

const rulesPlaceholder = ref(
  `rules:
  - DOMAIN,gemini.google.com,Openai`
)

const importRuleTypes = ['YAML']
const importRuleLoading = ref(false)
const importRules = ref({
  type: 'YAML',
  payload: ''
})

function close() {
  emit('update:modelValue', false)
}

async function importRule() {
  try {
    importRuleLoading.value = true
    const requestData = {
      vehicle: importRules.value.type,
      payload: importRules.value.payload
    }
    const result = await props.api.post('/plugin/ClashRuleProvider/import', requestData)
    if (!result.success) {
      emit('show-error', '规则导入失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '规则导入失败',
        color: 'error'
      })
      return
    }
    close()
    emit('refresh')
    // 显示成功提示
    emit('show-snackbar', {
      show: true,
      message: '规则导入成功',
      color: 'success'
    })
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', '导入规则失败: ' + (err.message || '未知错误'))
    }
    emit('show-snackbar', {
      show: true,
      message: '导入规则失败',
      color: 'error'
    })
  } finally {
    importRuleLoading.value = false
  }
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="40rem"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title>导入规则</v-card-title>
      <v-card-text style="max-height: 900px; overflow-y: auto">
        <v-select
          v-model="importRules.type"
          :items="importRuleTypes"
          label="内容格式"
          required
          class="mb-4"
        ></v-select>
        <VAceEditor
          v-model:value="importRules.payload"
          lang="yaml"
          theme="monokai"
          :options="editorOptions"
          :placeholder="rulesPlaceholder"
          style="height: 30rem; width: 100%; margin-bottom: 16px"
        />
        <v-alert type="info" dense class="mb-4" variant="tonal">
          请输入 Clash 规则中的 <strong>rules</strong> 字段，例如：<br />
          <code>rules:<br />- DOMAIN,gemini.google.com,Openai</code>
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="secondary" @click="close">取消</v-btn>
        <v-btn color="primary" :loading="importRuleLoading" @click="importRule">导入 </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
