<script setup lang="ts">
import { ref, computed, PropType, toRaw } from 'vue'
import debounce from 'lodash.debounce'
import { GeoRules, RuleData } from '@/components/types'

// 1. 定义 Props
const props = defineProps({
  // 父组件传递的规则数据
  initialRule: {
    type: Object as PropType<RuleData>,
    required: true
  },
  isAdding: {
    type: Boolean,
    default: true
  },
  editingType: {
    type: String,
    default: 'top'
  },
  ruleProviderNames: {
    type: Array as PropType<string[]>,
    default: () => []
  },
  geoRules: {
    type: Object as PropType<GeoRules>,
    default: () => ({ geoip: [], geosite: [] })
  },
  customOutbounds: {
    type: Array as PropType<string[]>,
    default: () => []
  },
  api: {
    type: Object,
    required: true
  }
})

// 2. 定义 Emits
// 使用 defineEmits 宏。传入一个字符串数组，列出组件会触发的事件
const emit = defineEmits(['close', 'refresh', 'show-snackbar', 'show-error'])

// 3. 响应式数据
// 将 props 中的 initialRule 复制到 rule 中，以便在组件内部修改而不影响父组件的 prop
const rule = ref<RuleData>(structuredClone(toRaw(props.initialRule)))

const loading = ref(false)
const ruleForm = ref<any>(null)
const geoSearch = ref('')
const geoIPSearch = ref('')
const geoFilterLoading = ref(false)
const filteredGeoItems = ref<string[]>([])
const ruleTypes = computed(() => {
  const allTypes = [
    'DOMAIN',
    'DOMAIN-SUFFIX',
    'DOMAIN-KEYWORD',
    'DOMAIN-REGEX',
    'DOMAIN-WILDCARD',
    'GEOSITE',
    'GEOIP',
    'IP-CIDR',
    'IP-CIDR6',
    'IP-SUFFIX',
    'IP-ASN',
    'SRC-GEOIP',
    'SRC-IP-ASN',
    'SRC-IP-CIDR',
    'SRC-IP-SUFFIX',
    'DST-PORT',
    'SRC-PORT',
    'IN-PORT',
    'IN-TYPE',
    'IN-USER',
    'IN-NAME',
    'PROCESS-PATH',
    'PROCESS-PATH-REGEX',
    'PROCESS-NAME',
    'PROCESS-NAME-REGEX',
    'UID',
    'NETWORK',
    'DSCP',
    'RULE-SET',
    'AND',
    'OR',
    'NOT',
    'SUB-RULE',
    'MATCH'
  ]

  // 如果是 ruleset 规则，过滤掉 SUB-RULE 和 RULE-SET
  if (props.editingType === 'ruleset') {
    return allTypes.filter((type) => !['SUB-RULE', 'RULE-SET'].includes(type))
  }
  return allTypes
})
const showAdditionalParams = computed(() => {
  return ['IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP'].includes(rule.value.type)
})

const onGeoSearch = (val: string) => {
  geoSearch.value = val
  performGeoSiteFilter(val)
}

const onGeoIPSearch = (val: string) => {
  geoIPSearch.value = val
  performGeoIPFilter(val)
}

const performGeoSiteFilter = debounce((val) => {
  if (!val) {
    filteredGeoItems.value = []
    geoFilterLoading.value = false
    return
  }
  geoFilterLoading.value = true
  filteredGeoItems.value = props.geoRules.geosite.filter((item) =>
    item.toLowerCase().includes(val.toLowerCase())
  )
  geoFilterLoading.value = false
}, 100) // 10ms debounce

const performGeoIPFilter = debounce((val) => {
  if (!val) {
    filteredGeoItems.value = []
    geoFilterLoading.value = false
    return
  }
  geoFilterLoading.value = true
  filteredGeoItems.value = props.geoRules.geoip.filter((item) =>
    item.toLowerCase().includes(val.toLowerCase())
  )
  geoFilterLoading.value = false
}, 200) // 20ms debounce

// 当输入框失去焦点时，将当前搜索词设置为选中项（如果它不在候选列表中）
const onGeoSiteBlur = () => {
  if (!filteredGeoItems.value.includes(geoSearch.value)) {
    rule.value.payload = geoSearch.value
  }
}
const onGeoIPBlur = () => {
  if (!filteredGeoItems.value.includes(geoIPSearch.value)) {
    rule.value.payload = geoIPSearch.value
  }
}

const actions = computed(() => [
  'DIRECT',
  'REJECT',
  'REJECT-DROP',
  'PASS',
  'COMPATIBLE',
  ...props.customOutbounds.map((outbound) => outbound)
])

const additionalParamOptions = ref([
  { title: '无', value: '' },
  { title: 'no-resolve', value: 'no-resolve' },
  { title: 'src', value: 'src' }
])

const payloadRules = computed(() => {
  return [
    (v: any) => {
      // 如果 type 是 'MATCH'，允许 payload 为空
      if (rule.value.type === 'MATCH') {
        return true // 不验证
      }
      // 否则，payload 不能为空
      return !!v || '内容不能为空'
    }
  ]
})

async function saveRule() {
  const { valid } = await ruleForm.value.validate()
  if (!valid) return
  loading.value = true
  try {
    if (rule.value?.payload) {
      rule.value.payload = rule.value.payload.trim()
    }
    const requestData = { ...rule.value }
    const priority = props.isAdding ? '' : `/${props.initialRule.priority}`
    const method = props.isAdding ? 'post' : 'patch'
    const result = await props.api[method](
      `/plugin/ClashRuleProvider/rules/${props.editingType}${priority}`,
      requestData
    )
    if (!result.success) {
      emit('show-error', '保存规则失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: '保存规则合失败',
        color: 'error'
      })
      return
    }
    emit('close')
    emit('refresh', ['top', 'ruleset'])
    emit('show-snackbar', {
      show: true,
      message: props.isAdding ? '规则添加成功' : '规则更新成功',
      color: 'success'
    })
  } catch (err: unknown) {
    if (err instanceof Error) emit('show-error', '保存规则失败: ' + (err.message || '未知错误'))
    emit('show-snackbar', {
      show: true,
      message: '保存规则失败',
      color: 'error'
    })
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <v-dialog max-width="40rem">
    <v-form ref="ruleForm" @submit.prevent="saveRule">
      <v-card>
        <v-card-title>{{ isAdding ? '添加规则' : '编辑规则' }}</v-card-title>
        <v-card-text>
          <v-select
            v-model="rule.type"
            :items="ruleTypes"
            label="规则类型"
            required
            class="mb-4"
          ></v-select>
          <v-select
            v-if="rule.type === 'RULE-SET'"
            v-model="rule.payload"
            :items="props.ruleProviderNames"
            label="选择规则集"
            required
            :rules="[(v) => !!v || '请选择一个有效的规则集']"
            class="mb-4"
          ></v-select>
          <v-autocomplete
            v-else-if="rule.type === 'GEOSITE'"
            v-model="rule.payload"
            :search="geoSearch"
            :items="filteredGeoItems"
            :loading="geoFilterLoading"
            hide-no-data
            hide-selected
            label="内容"
            no-filter
            solo
            :custom-filter="() => true"
            clearable
            class="mb-4"
            :rules="payloadRules"
            @update:search="onGeoSearch"
            @blur="onGeoSiteBlur"
          >
          </v-autocomplete>
          <v-autocomplete
            v-else-if="rule.type === 'GEOIP'"
            v-model="rule.payload"
            :search="geoIPSearch"
            :items="filteredGeoItems"
            :loading="geoFilterLoading"
            hide-no-data
            hide-selected
            label="内容"
            no-filter
            solo
            :custom-filter="() => true"
            clearable
            class="mb-4"
            :rules="payloadRules"
            @update:search="onGeoIPSearch"
            @blur="onGeoIPBlur"
          >
          </v-autocomplete>
          <v-combobox
            v-else-if="rule.type === 'AND' || rule.type === 'OR' || rule.type === 'NOT'"
            v-model="rule.conditions"
            label="条件"
            multiple
            chips
            hint="「(DOMAIN,baidu.com)」,「(NETWORK,TCP)」"
            clearable
            required
            class="mb-4"
          >
          </v-combobox>
          <v-text-field
            v-else-if="rule.type === 'SUB-RULE'"
            v-model="rule.condition"
            label="条件"
            required
            placeholder="(AND,(DOMAIN,baidu.com),(NETWORK,TCP))"
            :rules="payloadRules"
            class="mb-4"
          ></v-text-field>
          <v-text-field
            v-else
            v-model="rule.payload"
            label="内容"
            required
            :rules="payloadRules"
            class="mb-4"
          ></v-text-field>
          <v-text-field
            v-if="rule.type === 'SUB-RULE'"
            v-model="rule.action"
            label="子规则"
            required
            class="mb-4"
          ></v-text-field>
          <v-select
            v-else
            v-model="rule.action"
            :items="actions"
            label="出站"
            required
            class="mb-4"
          ></v-select>
          <v-select
            v-if="showAdditionalParams"
            v-model="rule.additional_params"
            label="附加参数"
            :items="additionalParamOptions"
            clearable
            hint="可选参数"
            persistent-hint
            class="mb-4"
          ></v-select>
          <v-text-field
            v-model.number="rule.priority"
            type="number"
            label="优先级"
            hint="数字越小优先级越高"
            persistent-hint
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="secondary" @click="emit('close')">取消</v-btn>
          <v-btn color="primary" type="submit" :loading="loading">保存 </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>
