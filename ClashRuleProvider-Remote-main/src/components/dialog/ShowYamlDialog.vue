<script setup lang="ts">
import { VAceEditor } from 'vue3-ace-editor'
import 'ace-builds/src-noconflict/ace'
import 'ace-builds/src-noconflict/mode-yaml'
import 'ace-builds/src-noconflict/theme-monokai'

// 输入参数
const props = defineProps({
  content: {
    type: String,
    required: true
  },
  placeholder: String
})

const readOnlyEditorOptions = {
  readOnly: true,
  enableBasicAutocompletion: true,
  enableSnippets: true,
  enableLiveAutocompletion: true,
  showLineNumbers: true,
  tabSize: 2
}

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'copyToClipboard', content: string): void
}>()
</script>

<template>
  <!-- YAML 对话框 -->
  <v-dialog :model-value="true" max-width="40rem" @update:model-value="emit('close')">
    <v-card>
      <v-card-title class="headline">YAML 配置</v-card-title>
      <v-card-text style="max-height: 600px; overflow-y: auto">
        <VAceEditor
          :value="props.content"
          lang="yaml"
          theme="monokai"
          :options="readOnlyEditorOptions"
          :placeholder="placeholder"
          style="height: 30rem; width: 100%; margin-bottom: 16px"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="emit('copyToClipboard', content)">复制</v-btn>
        <v-btn color="primary" @click="emit('close')">关闭</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
