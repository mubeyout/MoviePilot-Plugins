<script setup lang="ts">
import { PropType, ref, toRaw } from 'vue'
import { RuleProviderData } from '@/components/types'
import { defaultMetadata, defaultRuleProvider } from '@/components/constants'
import { isValidUrl } from '@/components/utils'

const props = defineProps({
  initialValue: {
    type: Object as PropType<RuleProviderData | null>,
    default: null
  },
  isAdding: {
    type: Boolean,
    default: true
  },
  api: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'refresh', 'show-snackbar', 'show-error'])

const ruleProviderTypes = ['http', 'file', 'inline']
const ruleProviderBehaviorTypes = ['domain', 'ipcidr', 'classical']
const ruleProviderFormatTypes = ['yaml', 'text', 'mrs']

const saveRuleProviderLoading = ref(false)
const newRuleProvider = ref<RuleProviderData>(
  props.initialValue
    ? structuredClone(toRaw(props.initialValue))
    : {
        meta: { ...defaultMetadata },
        data: { ...defaultRuleProvider },
        name: ''
      }
)
const ruleProvidersForm = ref<any>(null)

async function saveRuleProvider() {
  if (!ruleProvidersForm.value) return
  const { valid } = await ruleProvidersForm.value.validate()
  if (!valid) return
  try {
    saveRuleProviderLoading.value = true
    const name = encodeURIComponent(
      props.isAdding ? newRuleProvider.value.name : props.initialValue?.name || ''
    )
    const requestData = props.isAdding ? newRuleProvider.value.data : newRuleProvider.value
    const method = props.isAdding ? 'post' : 'patch'
    const result = await props.api[method](
      `/plugin/ClashRuleProvider/rule-providers/${name}`,
      requestData
    )
    if (!result.success) {
      emit('show-error', '保存规则集合失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '保存规则集合失败',
        color: 'error'
      })
      return
    }
    emit('show-snackbar', {
      show: true,
      message: props.isAdding ? '规则集合添加成功' : '规则集合更新成功',
      color: 'success'
    })
    emit('refresh')
    emit('close')
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', '保存规则集合失败: ' + (err.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '保存规则集合失败',
        color: 'error'
      })
    }
  } finally {
    saveRuleProviderLoading.value = false
  }
}
</script>

<template>
  <!-- Add/Edit Rule Provider Dialog -->
  <v-dialog max-width="40rem" :model-value="true" persistent>
    <v-form ref="ruleProvidersForm" @submit.prevent="saveRuleProvider">
      <v-card>
        <v-card-title>{{ isAdding ? '添加规则集合' : '编辑规则集合' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newRuleProvider.name"
            label="name"
            required
            :rules="[(v) => !!v || '名称不能为空']"
            class="mb-4"
          ></v-text-field>
          <v-select
            v-model="newRuleProvider.data.type"
            :items="ruleProviderTypes"
            label="type"
            required
            :rules="[(v) => !!v || '类型不能为空']"
            class="mb-4"
          ></v-select>
          <v-text-field
            v-if="newRuleProvider.data.type === 'http'"
            v-model="newRuleProvider.data.url"
            label="url"
            required
            :rules="[(v) => !!v || 'URL 不能为空', (v) => isValidUrl(v) || '请输入有效的 URL']"
            class="mb-4"
            hint="当类型为 http 时必须配置"
          ></v-text-field>
          <v-text-field
            v-if="newRuleProvider.data.type === 'file'"
            v-model="newRuleProvider.data.path"
            label="path"
            required
            :rules="[(v) => !!v || '当类型为文件时，路径不能为空']"
            class="mb-4"
            hint="文件路径，不填写时会使用 url 的 MD5 作为文件名"
          ></v-text-field>
          <v-text-field
            v-model.number="newRuleProvider.data.interval"
            label="interval"
            class="mb-4"
            type="number"
            min="0"
            suffix="s"
            hint="Provider 的更新间隔"
            clearable
            :rules="[(v) => v === null || v === undefined || v >= 0 || '更新间隔不能为负数']"
          ></v-text-field>
          <v-select
            v-model="newRuleProvider.data.behavior"
            :items="ruleProviderBehaviorTypes"
            label="behavior"
            class="mb-4"
            hint="对应不同格式的 rule-provider 文件"
          ></v-select>
          <v-select
            v-model="newRuleProvider.data.format"
            :items="ruleProviderFormatTypes"
            label="format"
            class="mb-4"
            hint="mrs目前 behavior 仅支持 domain/ipcidr"
          ></v-select>
          <v-text-field
            v-model.number="newRuleProvider.data['size-limit']"
            label="size-limit"
            class="mb-4"
            type="number"
            min="0"
            suffix="byte(s)"
            hint="可下载文件的最大大小，0 表示无限制"
            :rules="[(v) => v === null || v === undefined || v >= 0 || '大小限制不能为负数']"
          ></v-text-field>
          <v-combobox
            v-if="newRuleProvider.data.type === 'inline'"
            v-model="newRuleProvider.data.payload"
            multiple
            chips
            closable-chips
            clearable
            label="payload"
            required
            :rules="[(v) => !!v || '当类型为 inline 时，内容不能为空']"
            class="mb-4"
            hint="当类型为 inline 时才有效，按回车确认输入"
            row
          >
            <template #chip="{ props, item }">
              <v-chip v-bind="props" closable size="small">
                {{ item.value }}
              </v-chip>
            </template>
          </v-combobox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="secondary" @click="emit('close')">取消</v-btn>
          <v-btn color="primary" type="submit" :loading="saveRuleProviderLoading">保存 </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>

<style scoped></style>
