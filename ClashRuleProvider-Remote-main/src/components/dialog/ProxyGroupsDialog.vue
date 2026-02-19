<script setup lang="ts">
import { ref, computed, PropType, toRaw } from 'vue'
import { ProxyGroup, ProxyGroupData, ProxyProviderData } from '@/components/types'
import { isValidUrl } from '@/components/utils'
import { defaultProxyGroup } from '@/components/constants'

const props = defineProps({
  initialValue: {
    type: Object as PropType<ProxyGroupData | null>,
    default: null
  },
  isAdding: {
    type: Boolean,
    default: true
  },
  proxyProviders: {
    type: Array as PropType<ProxyProviderData[]>,
    default: () => []
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

const emit = defineEmits(['close', 'refresh', 'show-snackbar', 'show-error'])

const proxyGroup = ref<ProxyGroup>(
  props.initialValue ? structuredClone(toRaw(props.initialValue.data)) : { ...defaultProxyGroup }
)

const proxyGroupTypes = ref(['select', 'url-test', 'fallback', 'load-balance', 'smart'])

const form = ref<any>(null)
const loading = ref(false)
const proxyProviderNames = computed(() => Object.keys(props.proxyProviders))
const strategyTypes = ref(['round-robin', 'consistent-hashing', 'sticky-sessions'])
const smartStrategyTypes = ref(['round-robin', 'sticky-sessions'])
// 修改actions为计算属性，合并内置动作和自定义出站
const actions = computed(() => [
  'DIRECT',
  'REJECT',
  'REJECT-DROP',
  'PASS',
  'COMPATIBLE',
  ...props.customOutbounds.map((outbound) => outbound)
])

// 定义验证规则数组
const urlRules = [
  (v: string | null | undefined) => {
    // 规则：值v可以为空, 或者必须满足isValidUrl(v)的校验
    // 如果校验失败，则返回字符串作为错误提示
    return !v || isValidUrl(v) || '请输入一个有效的URL地址'
  }
]

async function saveProxyGroup() {
  if (!form.value) return
  const { valid } = await form.value.validate()
  if (!valid) return
  const name = encodeURIComponent(
    props.isAdding ? proxyGroup.value.name : props.initialValue?.data.name || ''
  )
  const action = props.isAdding ? '添加代理组' : '更新代理组'
  loading.value = true
  try {
    const path = props.isAdding ? '' : `/${name}`
    const method = props.isAdding ? 'post' : 'patch'

    // 清理数据，将空字符串转换为null，避免后端校验失败
    const cleanedProxyGroup = JSON.parse(JSON.stringify(toRaw(proxyGroup.value)))
    Object.keys(cleanedProxyGroup).forEach((key) => {
      if (cleanedProxyGroup[key] === '') {
        cleanedProxyGroup[key] = null
      }
    })

    const requestData = props.isAdding
      ? cleanedProxyGroup
      : {
          source: props.initialValue?.meta.source,
          proxy_group: cleanedProxyGroup
        }
    const result = await props.api[method](
      `/plugin/ClashRuleProvider/proxy-groups${path}`,
      requestData
    )
    if (!result.success) {
      emit('show-error', action + '失败: ' + (result.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: action + '失败',
        color: 'error'
      })
      return
    }
    emit('show-snackbar', {
      show: true,
      message: action + '成功',
      color: 'success'
    })
    emit('refresh')
    emit('close')
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', action + '失败: ' + (err.message || '未知错误'))
      emit('show-snackbar', {
        show: true,
        message: action + '失败',
        color: 'error'
      })
    }
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <v-dialog max-width="40rem">
    <v-form ref="form" @submit.prevent="saveProxyGroup">
      <v-card>
        <v-card-title>{{ props.isAdding ? '添加代理组' : '编辑代理组' }}</v-card-title>
        <v-card-text style="overflow-y: auto" max-height="60rem">
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="proxyGroup.name"
                label="name"
                required
                hint="策略组的名字"
                :rules="[(v) => !!v || 'Name不能为空']"
                class="mb-4"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="proxyGroup.type"
                label="type"
                :items="proxyGroupTypes"
                required
                hint="策略组的类型，smart组需要内核支持"
                class="mb-4"
              ></v-select>
            </v-col>
          </v-row>
          <v-select
            v-model="proxyGroup.proxies"
            label="proxies"
            :items="actions"
            multiple
            chips
            clearable
            hint="引入出站代理或其他策略组"
            class="mb-4"
          ></v-select>
          <v-select
            v-model="proxyGroup.use"
            label="use"
            :items="proxyProviderNames"
            multiple
            chips
            clearable
            hint="引入代理集合"
            class="mb-4"
          ></v-select>
          <v-text-field
            v-model="proxyGroup.url"
            label="url"
            hint="健康检查测试地址"
            :rules="urlRules"
            clearable
            class="mb-4"
          ></v-text-field>
          <v-text-field
            v-if="proxyGroup.type === 'url-test'"
            v-model.number="proxyGroup.tolerance"
            label="tolerance (ms)"
            variant="outlined"
            type="number"
            min="10"
            hint="节点切换容差"
            :rules="[(v) => v >= 0 || '容差需不小于0']"
            class="mb-4"
          ></v-text-field>
          <v-select
            v-if="proxyGroup.type === 'load-balance'"
            v-model="proxyGroup.strategy"
            label="strategy"
            :items="strategyTypes"
            hint="负载均衡策略"
            class="mb-4"
          ></v-select>
          <v-select
            v-if="proxyGroup.type === 'smart'"
            v-model="proxyGroup.strategy"
            label="strategy"
            :items="smartStrategyTypes"
            hint="负载均衡策略"
            class="mb-4"
          ></v-select>
          <v-row v-if="proxyGroup.type === 'smart'">
            <v-col cols="12" md="6">
              <v-text-field
                v-model="proxyGroup['policy-priority']"
                label="policy-priority"
                hint="优先级"
                clearable
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="proxyGroup['sample-rate']"
                label="sample-rate"
                type="number"
                hint="数据采集率"
                clearable
              ></v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="proxyGroup.filter"
                label="filter"
                hint="筛选满足关键词或正则表达式的节点"
                clearable
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="proxyGroup['exclude-filter']"
                label="exclude-filter"
                hint="排除满足关键词或正则表达式的节点"
                clearable
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="proxyGroup['exclude-type']"
                label="exclude-type"
                hint="不支持正则表达式，通过 | 分割"
                clearable
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="proxyGroup['expected-status']"
                label="expected-status"
                hint="健康检查时期望的 HTTP 响应状态码"
                clearable
              ></v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="12">
              <v-text-field
                v-model="proxyGroup.icon"
                label="icon"
                clearable
                hint="在 api 返回icon所输入的字符串"
              ></v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="proxyGroup.interval"
                label="interval"
                variant="outlined"
                type="number"
                min="0"
                clearable
                suffix="s"
                hint="健康检查间隔，如不为 0 则启用定时测试"
                :rules="[(v) => v === null || v === undefined || v > -1 || '检查间隔需不小于0']"
              >
                <template #prepend-inner>
                  <v-icon color="warning">mdi-timer</v-icon>
                </template>
              </v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="proxyGroup.timeout"
                label="timeout"
                variant="outlined"
                type="number"
                min="1"
                hint="请求的超时时间"
                suffix="ms"
                clearable
                :rules="[(v) => v === null || v === undefined || v > 0 || '超时时间必须大于0']"
              >
                <template #prepend-inner>
                  <v-icon color="warning">mdi-timer</v-icon>
                </template>
              </v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="proxyGroup['max-failed-times']"
                label="max-failed-times"
                variant="outlined"
                type="number"
                min="0"
                clearable
                hint="最大失败次数"
                :rules="[(v) => v >= 0 || '最大失败次数必须大于等于0']"
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup['lazy']"
                label="lazy"
                inset
                hint="未选择到当前策略组时，不进行测试"
                persistent-hint
              ></v-switch>
            </v-col>
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup['disable-udp']"
                label="disable-udp"
                inset
                hint="禁用该策略组的UDP"
                persistent-hint
              ></v-switch>
            </v-col>
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup.hidden"
                label="hidden"
                inset
                hint="在 api 返回hidden状态"
                persistent-hint
              ></v-switch>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup['include-all']"
                label="include-all"
                inset
                hint="引入所有出站代理以及代理集合"
                persistent-hint
              ></v-switch>
            </v-col>
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup['include-all-proxies']"
                label="include-all-proxies"
                inset
                hint="引入所有出站代理"
                persistent-hint
              ></v-switch>
            </v-col>
          </v-row>
          <v-row v-if="proxyGroup.type === 'smart'">
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup['uselightgbm']"
                label="uselightgbm"
                inset
                hint="使用LightGBM进行权重预测"
                persistent-hint
              ></v-switch>
            </v-col>
            <v-col cols="12" md="6">
              <v-switch
                v-model="proxyGroup['collectdata']"
                label="collectdata"
                inset
                hint="收集数据进行模型训练"
                persistent-hint
              ></v-switch>
            </v-col>
          </v-row>
        </v-card-text>
        <v-alert type="info" variant="tonal">
          参考<a
            href="https://wiki.metacubex.one/config/proxy-groups/"
            target="_blank"
            style="text-decoration: underline"
            >Docs</a
          >
        </v-alert>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="secondary" @click="emit('close')">取消</v-btn>
          <v-btn color="primary" type="submit" :loading="loading">保存 </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>
