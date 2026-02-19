<script setup lang="ts">
import { ref, reactive, onMounted, computed, PropType } from 'vue'
import { VAceEditor } from 'vue3-ace-editor'
import 'ace-builds/src-noconflict/ace'
import 'ace-builds/src-noconflict/mode-yaml'
import 'ace-builds/src-noconflict/theme-monokai'
import { validateIPs, isValidUrl } from '@/components/utils'
import { PluginConfig } from '@/components/types'
// Props
const props = defineProps({
  initialConfig: {
    type: Object as PropType<Record<string, any>>,
    default: () => ({})
  },
  api: {
    type: Object,
    default: () => {}
  }
})

// 自定义事件
const emit = defineEmits(['save', 'close', 'switch'])

const activeTab = ref('subscription')
const editorOptions = {
  enableBasicAutocompletion: true,
  enableSnippets: true,
  enableLiveAutocompletion: true,
  showLineNumbers: true,
  tabSize: 2
}
const configPlaceholder = ref(
  `profile:
  store-selected: true
mode: rule
log-level: silent`
)

// 状态变量
const clashTemplateDialog = ref(false)
const clashTemplateType = ref('YAML')
const clashTemplateContent = ref('')
const form = ref<any>(null)
const isFormValid = ref(true)
const error = ref<string>('')
const saving = ref(false)
const savingTemplate = ref(false)
const testing = ref(false)
const dashboardComponents = ['Clash Info', 'Traffic Stats']
const showSecrets = ref<Record<number, boolean>>({ 0: false })

// Test result state
const testResult = reactive({
  show: false,
  success: false,
  title: '',
  message: ''
})

// 默认配置
const defaultConfig: PluginConfig = {
  enabled: false,
  subscriptions_config: [],
  filter_keywords: ['公益性', '高延迟', '域名', '官网', '重启', '过期时间', '系统代理'],
  clash_dashboards: [{ url: '', secret: '' }],
  movie_pilot_url: '',
  cron_string: '0 */6 * * *',
  timeout: 10,
  retry_times: 3,
  proxy: false,
  notify: false,
  auto_update_subscriptions: true,
  ruleset_prefix: '📂<=',
  acl4ssr_prefix: '🗂️=>',
  group_by_region: false,
  group_by_country: false,
  refresh_delay: 5,
  enable_acl4ssr: false,
  dashboard_components: [],
  clash_template: '',
  hint_geo_dat: false,
  best_cf_ip: [],
  active_dashboard: 0,
  apikey: null,
  identifiers: [],
  cache_ttl: 3600
}

// 响应式配置对象
const config = reactive({ ...defaultConfig })

// 初始化
onMounted(() => {
  if (props.initialConfig) {
    Object.keys(props.initialConfig).forEach((key) => {
      if (key in config) {
        ;(config as any)[key] = props.initialConfig[key]
      }
    })
  }
})

const sub_links = computed(() => {
  if (!config.subscriptions_config) {
    return []
  }
  return config.subscriptions_config.map((item) => item.url)
})

const generateApiKey = () => {
  // 简单生成随机字符串，可替换为更安全的算法
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let key = ''
  for (let i = 0; i < 32; i++) {
    key += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  config.apikey = key
}

function showError(title: string, msg: string) {
  testResult.title = title
  testResult.success = false
  testResult.message = msg
  testResult.show = true
}

// 测试连接
async function testConnection() {
  testing.value = true
  error.value = ''
  testResult.show = false

  try {
    // 验证必需的参数
    if (sub_links.value.length === 0) {
      showError('连接测试失败', '请先配置至少一个订阅链接')
    }

    // 准备API请求参数
    const testParams = {
      clash_apis: config.clash_dashboards,
      sub_links: sub_links.value
    }

    // 调用API进行连接测试
    const result = await props.api.post('/plugin/ClashRuleProvider/connectivity', testParams)

    // 根据返回结果显示相应消息
    if (result.success) {
      testResult.success = true
      testResult.title = '连接测试成功！'
      testResult.message = 'Clash面板和订阅链接连接正常，配置验证通过'
      testResult.show = true

      // Auto hide after 5 seconds
      setTimeout(() => {
        testResult.show = false
      }, 5000)
    } else {
      showError('连接测试失败', result.message || '连接测试失败，请检查配置')
    }
  } catch (err: unknown) {
    if (err instanceof Error) showError('连接测试失败', err.message)
  } finally {
    testing.value = false
  }
}

// 保存配置
async function saveConfig() {
  // 手动验证所有订阅链接
  for (let i = 0; i < config.subscriptions_config.length; i++) {
    const sub = config.subscriptions_config[i]
    if (!sub.url || !isValidUrl(sub.url)) {
      error.value = `订阅配置 ${i + 1} 中的URL无效或为空`
      // 展开对应的面板以提示用户
      // 注意：这需要给 v-expansion-panel 设置一个 ref 或者 model 来控制展开状态
      return
    }
  }

  if (!isFormValid.value) {
    error.value = '请修正表单中的错误'
    return
  }

  saving.value = true
  error.value = ''

  try {
    await new Promise((resolve) => setTimeout(resolve, 1000))
    emit('save', { ...config })
  } catch (err: unknown) {
    if (err instanceof Error) error.value = err.message || '保存配置失败'
  } finally {
    saving.value = false
  }
}

const toggleSecret = (index: number) => {
  showSecrets.value[index] = !showSecrets.value[index]
}
const addClashConfig = () => {
  const newIndex = config.clash_dashboards.length
  config.clash_dashboards.push({ url: '', secret: '' })
  showSecrets.value[newIndex] = false
}

const removeClashConfig = (index: number) => {
  config.clash_dashboards.splice(index, 1)
  delete showSecrets.value[index]

  // 如果删除的是当前激活项，重置激活
  if (config.active_dashboard === index) {
    config.active_dashboard = config.clash_dashboards.length > 0 ? 0 : null
  }
}

const addSubscriptionConfig = () => {
  config.subscriptions_config.push({
    url: '',
    rules: false,
    proxies: true,
    'proxy-groups': false,
    'rule-providers': false,
    'proxy-providers': false
  })
}

const removeSubscriptionConfig = (index: number) => {
  config.subscriptions_config.splice(index, 1)
}

async function openClashTemplateDialog() {
  // 从后端获取配置模板
  try {
    const result = await props.api.get('/plugin/ClashRuleProvider/template')
    if (result.success && result.data && result.data.template) {
      clashTemplateContent.value = result.data.template
    } else {
      // 如果后端没有模板，使用配置中的模板
      clashTemplateContent.value = config.clash_template || ''
    }
  } catch (err: unknown) {
    // 如果获取失败，使用配置中的模板
    console.error('Failed to load template from backend:', err)
    clashTemplateContent.value = config.clash_template || ''
  }
  clashTemplateDialog.value = true
}

async function saveClashTemplateToBackend() {
  try {
    savingTemplate.value = true
    const result = await props.api.put('/plugin/ClashRuleProvider/template', { template: clashTemplateContent.value })
    if (result.success) {
      config.clash_template = clashTemplateContent.value
      clashTemplateDialog.value = false
      testResult.success = true
      testResult.title = '保存成功'
      testResult.message = '配置模板已保存到后端'
      testResult.show = true
      setTimeout(() => {
        testResult.show = false
      }, 3000)
    } else {
      showError('保存失败', result.message || '配置模板保存失败')
    }
  } catch (err: unknown) {
    if (err instanceof Error) showError('保存失败', err.message)
  } finally {
    savingTemplate.value = false
  }
}

function saveClashTemplate() {
  config.clash_template = clashTemplateContent.value
  clashTemplateDialog.value = false
}

// 重置表单
function resetForm() {
  Object.assign(config, JSON.parse(JSON.stringify(defaultConfig)))

  if (form.value) {
    form.value.resetValidation()
  }
}
</script>
<template>
  <div class="plugin-config">
    <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>
    <v-card>
      <v-card-item>
        <v-card-title>Clash Rule Provider 插件配置</v-card-title>
        <template #append>
          <v-btn icon color="primary" variant="text" @click="emit('close')">
            <v-icon left>mdi-close</v-icon>
          </v-btn>
        </template>
      </v-card-item>
      <v-card-text class="overflow-y-auto">
        <v-form ref="form" v-model="isFormValid" @submit.prevent="saveConfig">
          <!-- 标签页 -->
          <v-row>
            <v-col cols="6" md="3">
              <v-switch
                v-model="config.enabled"
                label="启用插件"
                color="primary"
                inset
                density="compact"
                hint="启用插件"
              />
            </v-col>
            <v-col cols="6" md="3">
              <v-switch
                v-model="config.proxy"
                label="启用代理"
                color="primary"
                inset
                density="compact"
                hint="是否使用系统代理进行网络请求"
              />
            </v-col>
            <v-col cols="6" md="3">
              <v-switch
                v-model="config.notify"
                label="启用通知"
                color="primary"
                inset
                density="compact"
                hint="执行完成后发送通知消息"
              />
            </v-col>
            <v-col cols="6" md="3">
              <v-switch
                v-model="config.auto_update_subscriptions"
                label="自动更新订阅"
                color="primary"
                inset
                density="compact"
                hint="定期自动更新 Clash 订阅配置"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="config.movie_pilot_url"
                label="MoviePilot URL"
                variant="outlined"
                placeholder="http://localhost:3001"
                hint="MoviePilot 服务的访问地址"
                :rules="[
                  (v) => !!v || 'MoviePilot URL不能为空',
                  (v) => isValidUrl(v) || '请输入有效的URL地址'
                ]"
              >
                <template #prepend-inner>
                  <v-icon color="success">mdi-movie</v-icon>
                </template>
              </v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="config.apikey"
                label="API Key"
                variant="outlined"
                placeholder="留空使用系统 API Key"
                hint="用于服务认证的 API Key"
              >
                <template #prepend-inner>
                  <v-icon color="warning">mdi-key</v-icon>
                </template>
                <template #append-inner>
                  <v-icon color="primary" class="cursor-pointer" @click="generateApiKey">
                    mdi-autorenew
                  </v-icon>
                </template>
              </v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-select
                v-model="config.dashboard_components"
                :items="dashboardComponents"
                label="仪表盘组件"
                hide-details
                variant="outlined"
                multiple
                chips
                class="mb-4"
                hint="添加仪表盘组件"
              >
                <template #prepend-inner>
                  <v-icon color="info">mdi-view-dashboard</v-icon>
                </template>
              </v-select>
            </v-col>
          </v-row>
          <v-tabs v-model="activeTab" class="mt-4" grow>
            <v-tab value="subscription">
              <v-icon start>mdi-link-variant</v-icon>
              订阅配置
            </v-tab>
            <v-tab value="clash">
              <v-icon start>mdi-application-brackets</v-icon>
              Clash API 配置
            </v-tab>
            <v-tab value="execution">
              <v-icon start>mdi-play-circle</v-icon>
              执行设置
            </v-tab>
            <v-tab value="settings">
              <v-icon start>mdi-cog</v-icon>
              高级选项
            </v-tab>
          </v-tabs>

          <v-divider></v-divider>

          <!-- 标签页内容 -->
          <v-window v-model="activeTab" class="pa-4">
            <!-- 订阅配置 -->
            <v-window-item value="subscription">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch
                    v-model="config.group_by_country"
                    label="按国家分组节点"
                    color="primary"
                    inset
                    hint="启用后，根据名称将节点添加到代理组"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-switch
                    v-model="config.group_by_region"
                    label="按大洲分组节点"
                    color="primary"
                    inset
                    hint="启用后，根据名称将节点添加到代理组"
                  />
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12">
                  <v-combobox
                    v-model="config.filter_keywords"
                    label="节点过滤关键词"
                    variant="outlined"
                    multiple
                    chips
                    closable-chips
                    clearable
                    hint="添加用于过滤节点的关键词"
                  >
                    <template #prepend-inner>
                      <v-icon color="info">mdi-filter</v-icon>
                    </template>
                    <template #chip="{ props, item }">
                      <v-chip v-bind="props" closable size="small" color="info">
                        {{ item.value }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-col>
                <v-divider></v-divider>
                <v-col cols="12">
                  <v-expansion-panels multiple>
                    <v-expansion-panel
                      v-for="(item, index) in config.subscriptions_config"
                      :key="index"
                    >
                      <v-expansion-panel-title>
                        <span class="text-subtitle-1 font-weight-medium">
                          订阅配置 {{ index + 1 }}
                        </span>
                        <v-spacer />
                        <v-btn
                          icon
                          size="small"
                          color="error"
                          variant="text"
                          @click.stop="removeSubscriptionConfig(index)"
                        >
                          <v-icon>mdi-delete</v-icon>
                        </v-btn>
                      </v-expansion-panel-title>

                      <v-expansion-panel-text>
                        <v-row dense>
                          <v-col cols="12">
                            <v-text-field
                              v-model="item.url"
                              label="订阅链接"
                              variant="underlined"
                              placeholder="https://xxx.com/clash/config.yaml"
                              density="compact"
                              :rules="[
                                (v) => !!v || '订阅链接不能为空',
                                (v) => isValidUrl(v) || '请输入有效的 URL 地址'
                              ]"
                            >
                              <template #prepend-inner>
                                <v-icon color="primary">mdi-link</v-icon>
                              </template>
                            </v-text-field>
                          </v-col>

                          <v-col cols="12" md="3">
                            <v-switch
                              v-model="item.rules"
                              label="保留规则"
                              color="primary"
                              density="compact"
                            />
                          </v-col>
                          <v-col cols="12" md="3">
                            <v-switch
                              v-model="item['rule-providers']"
                              label="保留规则集合"
                              color="primary"
                              density="compact"
                            />
                          </v-col>
                          <v-col cols="12" md="3">
                            <v-switch
                              v-model="item['proxy-groups']"
                              label="保留代理组"
                              color="primary"
                              density="compact"
                            />
                          </v-col>
                          <v-col cols="12" md="3">
                            <v-switch
                              v-model="item['proxy-providers']"
                              label="保留代理集合"
                              color="primary"
                              density="compact"
                            />
                          </v-col>
                        </v-row>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>

                  <v-row dense justify="space-between">
                    <v-btn
                      size="small"
                      color="primary"
                      variant="tonal"
                      class="mt-2"
                      @click="addSubscriptionConfig"
                    >
                      <v-icon start>mdi-plus</v-icon>
                      添加
                    </v-btn>
                    <v-btn
                      size="small"
                      color="primary"
                      variant="tonal"
                      class="mt-2"
                      @click="openClashTemplateDialog"
                    >
                      <v-icon left>mdi-import</v-icon>
                      配置模板
                    </v-btn>
                  </v-row>
                </v-col>
              </v-row>
            </v-window-item>

            <!-- Clash API 配置 -->
            <v-window-item value="clash">
              <v-alert
                border-color="info"
                variant="tonal"
                border="start"
                text="Clash 访问地址用于通知 Clash 更新规则集; 选中的面板用于小组件显示"
                class="mb-3"
              ></v-alert>
              <v-row>
                <v-col cols="12">
                  <!-- 使用 v-radio-group 来管理单选按钮组 -->
                  <v-radio-group v-model="config.active_dashboard">
                    <v-row v-for="(item, index) in config.clash_dashboards" :key="index">
                      <!-- 选择激活 -->
                      <v-col cols="2" md="1" class="d-flex align-center">
                        <v-radio :value="index" color="primary" label="" />
                      </v-col>
                      <v-col cols="10" md="5">
                        <v-text-field
                          v-model="item.url"
                          label="API URL"
                          variant="outlined"
                          placeholder="http://localhost:9090"
                          density="compact"
                          :rules="[(v) => !v || isValidUrl(v) || '请输入有效的URL地址']"
                        >
                          <template #prepend-inner>
                            <v-icon color="primary">mdi-web</v-icon>
                          </template>
                        </v-text-field>
                      </v-col>

                      <v-col cols="10" md="5">
                        <v-text-field
                          v-model="item.secret"
                          label="API 密钥"
                          variant="outlined"
                          placeholder="your-clash-secret"
                          density="compact"
                          :append-inner-icon="showSecrets[index] ? 'mdi-eye-off' : 'mdi-eye'"
                          :type="showSecrets[index] ? 'text' : 'password'"
                          @click:append-inner="toggleSecret(index)"
                        >
                          <template #prepend-inner>
                            <v-icon color="warning">mdi-key</v-icon>
                          </template>
                        </v-text-field>
                      </v-col>

                      <v-col cols="2" md="1" class="d-flex align-center">
                        <v-btn icon color="error" variant="text" @click="removeClashConfig(index)">
                          <v-icon>mdi-delete</v-icon>
                        </v-btn>
                      </v-col>
                    </v-row>
                  </v-radio-group>
                  <v-btn
                    size="small"
                    color="primary"
                    variant="tonal"
                    class="mt-2"
                    @click="addClashConfig"
                  >
                    <v-icon start>mdi-plus</v-icon>
                    添加
                  </v-btn>
                </v-col>
              </v-row>
            </v-window-item>

            <!-- 执行设置 -->
            <v-window-item value="execution">
              <v-row>
                <v-col cols="12" md="6">
                  <v-cron-field
                    v-model="config.cron_string"
                    label="执行周期"
                    placeholder="0 4 * * *"
                    hint="使用标准Cron表达式格式 (分 时 日 月 周)"
                  >
                    <template #prepend-inner>
                      <v-icon color="info">mdi-clock-time-four-outline</v-icon>
                    </template>
                  </v-cron-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.timeout"
                    label="超时时间"
                    variant="outlined"
                    type="number"
                    min="1"
                    max="300"
                    suffix="秒"
                    hint="请求的超时时间"
                    :rules="[(v) => v > 0 || '超时时间必须大于0']"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.retry_times"
                    label="重试次数"
                    variant="outlined"
                    type="number"
                    min="0"
                    max="10"
                    hint="失败时的重试次数"
                    :rules="[(v) => v >= 0 || '重试次数不能为负数']"
                  >
                    <template #prepend-inner>
                      <v-icon color="info">mdi-refresh</v-icon>
                    </template>
                  </v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.refresh_delay"
                    label="刷新延迟"
                    variant="outlined"
                    type="number"
                    min="1"
                    max="30"
                    suffix="秒"
                    hint="通知Clash刷新规则集的延迟时间"
                    :rules="[(v) => v >= 0 || '刷新延迟不能为负数']"
                  >
                    <template #prepend-inner>
                      <v-icon color="info">mdi-clock-outline</v-icon>
                    </template>
                  </v-text-field>
                </v-col>
              </v-row>
            </v-window-item>
            <!-- 高级选项 -->
            <v-window-item value="settings">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch
                    v-model="config.hint_geo_dat"
                    label="Geo规则补全"
                    color="primary"
                    inset
                    hint="获取官方Geo数据库, 并在输入时补全"
                  ></v-switch>
                </v-col>
                <v-col cols="12" md="6">
                  <v-switch
                    v-model="config.enable_acl4ssr"
                    label="ACL4SSR规则集"
                    color="primary"
                    inset
                    hint="启用ACL4SSR规则集"
                  ></v-switch>
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="config.ruleset_prefix"
                    label="规则集前缀"
                    variant="outlined"
                    placeholder="📂<="
                    hint="为生成的规则集添加前缀"
                  >
                    <template #prepend-inner>
                      <v-icon color="info">mdi-palette</v-icon>
                    </template>
                  </v-text-field>
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="config.acl4ssr_prefix"
                    label="ACL4SSR 规则集前缀"
                    variant="outlined"
                    placeholder="🗂️=>"
                    hint="ACL4SSR 规则集前缀"
                  >
                    <template #prepend-inner>
                      <v-icon color="primary">mdi-palette</v-icon>
                    </template>
                  </v-text-field>
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="config.cache_ttl"
                    label="缓存 TTL"
                    variant="outlined"
                    placeholder="3600"
                    type="number"
                    min="600"
                    suffix="秒"
                  >
                    <template #prepend-inner>
                      <v-icon color="warning">mdi-alarm</v-icon>
                    </template>
                  </v-text-field>
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12" md="12">
                  <v-combobox
                    v-model="config.best_cf_ip"
                    label="Cloudflare CDN 优选 IPs"
                    variant="outlined"
                    multiple
                    chips
                    closable-chips
                    clearable
                    hint="用于设置 Hosts 中的 Cloudflare 域名"
                    :rules="[validateIPs]"
                  >
                    <template #chip="{ props, item }">
                      <v-chip v-bind="props" closable size="small">
                        {{ item.value }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12" md="12">
                  <v-combobox
                    v-model="config.identifiers"
                    label="预设设备标识"
                    variant="outlined"
                    multiple
                    chips
                    closable-chips
                    clearable
                    hint="获取配置时的额外查询参数 「identifier」"
                  >
                    <template #chip="{ props, item }">
                      <v-chip v-bind="props" closable size="small">
                        {{ item.value }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-col>
              </v-row>
            </v-window-item>
          </v-window>
        </v-form>
      </v-card-text>
      <v-alert type="info" variant="tonal">
        配置说明参考:
        <a
          href="https://github.com/wumode/MoviePilot-Plugins/tree/main/plugins.v2/clashruleprovider/README.md"
          target="_blank"
          style="text-decoration: underline"
          >README</a
        >
      </v-alert>
      <v-card-actions>
        <v-btn color="primary" @click="emit('switch')">
          <v-icon left>mdi-view-dashboard-edit</v-icon>
          规则
        </v-btn>
        <v-btn color="secondary" @click="resetForm">
          <v-icon left>mdi-autorenew</v-icon>
          重置
        </v-btn>
        <v-btn color="info" :loading="testing" @click="testConnection">
          <v-icon left>mdi-connection</v-icon>
          测试连接
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" :disabled="!isFormValid" :loading="saving" @click="saveConfig">
          <v-icon left>mdi-content-save</v-icon>
          保存配置
        </v-btn>
      </v-card-actions>

      <!-- Simple Test Result Alert -->
      <v-alert
        v-if="testResult.show"
        :type="testResult.success ? 'success' : 'error'"
        variant="tonal"
        closable
        class="ma-4 mt-0"
        @click:close="testResult.show = false"
      >
        <div class="d-flex align-center">
          <v-icon class="mr-2">
            {{ testResult.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}
          </v-icon>
          <div>
            <div class="font-weight-medium">{{ testResult.title }}</div>
            <div class="text-body-2">{{ testResult.message }}</div>
          </div>
        </div>
      </v-alert>
    </v-card>
  </div>
  <v-dialog v-model="clashTemplateDialog" max-width="600">
    <v-card>
      <v-card-title>Clash 配置模板</v-card-title>
      <v-card-text style="max-height: 900px; overflow-y: auto">
        <v-select
          v-model="clashTemplateType"
          :items="['YAML']"
          label="配置类型"
          class="mb-4"
          disabled
        ></v-select>
        <VAceEditor
          v-model:value="clashTemplateContent"
          lang="yaml"
          theme="monokai"
          hint=""
          :options="editorOptions"
          :placeholder="configPlaceholder"
          style="height: 30rem; width: 100%; margin-bottom: 16px"
        />
        <v-alert type="info" dense class="mb-4" variant="tonal">
          规则和出站代理会被添加在配置模板上。<br>
          <strong>确定</strong>：仅更新本地配置，需点击保存配置按钮才生效<br>
          <strong>保存到后端</strong>：直接保存到后端，立即生效
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="clashTemplateDialog = false">取消</v-btn>
        <v-btn color="default" @click="saveClashTemplate">确定</v-btn>
        <v-btn color="primary" :loading="savingTemplate" @click="saveClashTemplateToBackend">保存到后端</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<style scoped>
.plugin-config {
  margin: 0 auto;
}
</style>
