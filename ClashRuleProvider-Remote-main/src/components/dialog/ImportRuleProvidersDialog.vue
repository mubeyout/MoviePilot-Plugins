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

const ruleProvidersPlaceholder = ref(
  `rule-providers:
  YouTube:
    type: http
    url: https://example.com/rules.yaml
    behavior: classical
    format: yaml`
)

const importRuleProvidersTypes = ['YAML']
const importRuleProvidersLoading = ref(false)
const importRuleProviders = ref({
  type: 'YAML',
  payload: ''
})

function close() {
  emit('update:modelValue', false)
}

async function importProviders() {
  try {
    importRuleProvidersLoading.value = true
    const requestData = {
      vehicle: importRuleProviders.value.type,
      payload: importRuleProviders.value.payload
    }
    const result = await props.api.post('/plugin/ClashRuleProvider/rule-providers/import', requestData)
    if (!result.success) {
      emit('show-error', '规则集合导入失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '规则集合导入失败',
        color: 'error'
      })
      return
    }
    close()
    emit('refresh')
    emit('show-snackbar', {
      show: true,
      message: '规则集合导入成功',
      color: 'success'
    })
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', '导入规则集合失败: ' + (err.message || '未知错误'))
    }
    emit('show-snackbar', {
      show: true,
      message: '导入规则集合失败',
      color: 'error'
    })
  } finally {
    importRuleProvidersLoading.value = false
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
      <v-card-title>导入规则集合</v-card-title>
      <v-card-text style="max-height: 900px; overflow-y: auto">
        <v-select
          v-model="importRuleProviders.type"
          :items="importRuleProvidersTypes"
          label="内容格式"
          required
          class="mb-4"
        ></v-select>
        <VAceEditor
          v-model:value="importRuleProviders.payload"
          lang="yaml"
          theme="monokai"
          :options="editorOptions"
          :placeholder="ruleProvidersPlaceholder"
          style="height: 30rem; width: 100%; margin-bottom: 16px"
        />
        <v-alert type="info" dense class="mb-4" variant="tonal">
          请输入 Clash 配置中的 <strong>rule-providers</strong> 字段，例如：<br />
          <code>rule-providers:<br />  YouTube:<br />    type: http<br />    url: https://example.com/rules.yaml<br />    behavior: classical</code>
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="secondary" @click="close">取消</v-btn>
        <v-btn color="primary" :loading="importRuleProvidersLoading" @click="importProviders">导入</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
