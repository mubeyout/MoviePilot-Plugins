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

const proxyGroupsPlaceholder = ref(
  `proxy-groups:
  - name: 选择组
    type: select
    proxies:
      - proxy1
      - proxy2`
)

const importProxyGroupsTypes = ['YAML']
const importProxyGroupsLoading = ref(false)
const importProxyGroups = ref({
  type: 'YAML',
  payload: ''
})

function close() {
  emit('update:modelValue', false)
}

async function importGroups() {
  try {
    importProxyGroupsLoading.value = true
    const requestData = {
      vehicle: importProxyGroups.value.type,
      payload: importProxyGroups.value.payload
    }
    const result = await props.api.post('/plugin/ClashRuleProvider/proxy-groups/import', requestData)
    if (!result.success) {
      emit('show-error', '代理组导入失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '代理组导入失败',
        color: 'error'
      })
      return
    }
    close()
    emit('refresh')
    emit('show-snackbar', {
      show: true,
      message: '代理组导入成功',
      color: 'success'
    })
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', '导入代理组失败: ' + (err.message || '未知错误'))
    }
    emit('show-snackbar', {
      show: true,
      message: '导入代理组失败',
      color: 'error'
    })
  } finally {
    importProxyGroupsLoading.value = false
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
      <v-card-title>导入代理组</v-card-title>
      <v-card-text style="max-height: 900px; overflow-y: auto">
        <v-select
          v-model="importProxyGroups.type"
          :items="importProxyGroupsTypes"
          label="内容格式"
          required
          class="mb-4"
        ></v-select>
        <VAceEditor
          v-model:value="importProxyGroups.payload"
          lang="yaml"
          theme="monokai"
          :options="editorOptions"
          :placeholder="proxyGroupsPlaceholder"
          style="height: 30rem; width: 100%; margin-bottom: 16px"
        />
        <v-alert type="info" dense class="mb-4" variant="tonal">
          请输入 Clash 配置中的 <strong>proxy-groups</strong> 字段，例如：<br />
          <code>proxy-groups:<br />  - name: 选择组<br />    type: select<br />    proxies:<br />      - proxy1</code>
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="secondary" @click="close">取消</v-btn>
        <v-btn color="primary" :loading="importProxyGroupsLoading" @click="importGroups">导入</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
