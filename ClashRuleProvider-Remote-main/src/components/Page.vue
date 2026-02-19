<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import yaml from 'js-yaml'
import ShowYamlDialog from './dialog/ShowYamlDialog.vue'
import DataVisibilityDialog from './dialog/DataVisibilityDialog.vue'
import TopRulesTab from './tabs/TopRulesTab.vue'
import ProxyGroupsTab from './tabs/ProxyGroupsTab.vue'
import ProxiesTab from './tabs/ProxiesTab.vue'
import SubscriptionTab from './tabs/SubscriptionTab.vue'
import RuleProvidersTab from './tabs/RuleProvidersTab.vue'
import StatisticsPanel from './StatisticsPanel.vue'
import MetaLogo from '@/assets/Meta.png'
import '@/styles/common.css'
import {
  RuleData,
  ProxyGroupData,
  RuleProviderData,
  ProxyData,
  SubscriptionInfo,
  GeoRules,
  ProxyProviderData,
  Metadata
} from '@/components/types'
import { defaultMetadata } from '@/components/constants'

// 接收初始配置
const props = defineProps({
  model: {
    type: Object,
    default: () => {}
  },
  api: {
    type: Object,
    default: () => {}
  }
})

// 自定义事件，用于通知主应用刷新数据
const emit = defineEmits(['action', 'switch', 'close'])

const activeTab = ref(0)

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})
// 添加自定义出站状态
const customOutbounds = ref<string[]>([])

const subUrl = ref('')
const proxyGroups = ref<ProxyGroupData[]>([])
const proxyProviders = ref<ProxyProviderData[]>([])
const proxies = ref<ProxyData[]>([])
const presetIdentifiers = ref<string[]>([])

// 组件状态
const expand = ref(false)
const loading = ref(true)
const error = ref<boolean>(false)
const errorMsg = ref<string>('')
const rules = ref<RuleData[]>([])
const ruleProviders = ref<RuleProviderData[]>([])
const status = ref('running')
const rulesetPrefix = ref('📂<=')
const geoRules = ref<GeoRules>({
  geoip: [],
  geosite: []
})
const lastUpdated = ref('')
const showYamlDialog = ref(false)
const displayedYaml = ref('')

// Visibility Dialog State
const visibilityDialogVisible = ref(false)
const currentVisibilityMeta = ref<Metadata>({ ...defaultMetadata })
const currentVisibilityEndpoint = ref('')
const currentVisibilityRegion = ref('')

// 排序后的规则
const sortedRules = computed<RuleData[]>(() =>
  [...rules.value].sort((a, b) => a.priority - b.priority)
)
const ruleProviderNames = computed(() => {
  return ruleProviders.value.map((provider) => provider.name)
})

const subscriptionsInfo = ref<Record<string, SubscriptionInfo>>({})
const bestCloudflareIPs = ref([])

// 复制功能
function copyToClipboard(text: string) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      snackbar.value = {
        show: true,
        message: '已复制到剪贴板',
        color: 'success'
      }
    })
    .catch(() => {
      snackbar.value = {
        show: true,
        message: '复制失败',
        color: 'error'
      }
    })
}

function copyPluginLink() {
  const url = `${window.location.origin}/#/plugins?tab=installed&id=ClashRuleProvider`
  copyToClipboard(url)
}

function generateIdentifierUrl(identifier: string) {
  if (!subUrl.value) return ''
  try {
    const url = new URL(subUrl.value, window.location.origin)
    url.searchParams.set('identifier', identifier)
    return url.toString()
  } catch (e) {
    console.error('Failed to parse URL', e)
    return subUrl.value
  }
}

function showYaml(obj: any) {
  // 生成 YAML 并显示
  displayedYaml.value = yaml.dump(obj)
  showYamlDialog.value = true
}

function showError(Msg: string) {
  error.value = true
  errorMsg.value = Msg
}

function handleEditVisibility(meta: Metadata, endpoint: string, region: string) {
  currentVisibilityMeta.value = meta
  currentVisibilityEndpoint.value = endpoint
  currentVisibilityRegion.value = region
  visibilityDialogVisible.value = true
}

async function refreshStatus() {
  const state = await props.api.get('/plugin/ClashRuleProvider/status')
  // 处理状态请求的响应
  status.value = state?.data?.state ? 'running' : 'disabled'
  subUrl.value = state?.data?.sub_url || ''

  if (state?.data?.subscription_info) {
    subscriptionsInfo.value = state.data.subscription_info
  }
  bestCloudflareIPs.value = state?.data?.best_cf_ip || []
  rulesetPrefix.value = state?.data?.ruleset_prefix || '📂<='
  geoRules.value = state?.data?.geoRules ?? geoRules.value
}

async function refreshTopRules() {
  const response = await props.api.get('/plugin/ClashRuleProvider/rules/top')
  rules.value = response?.data || []
}

async function refreshOutbounds() {
  const outboundsResponse = await props.api.get('/plugin/ClashRuleProvider/clash-outbound')
  customOutbounds.value = outboundsResponse?.data || []
}

async function refreshExtraRuleProviders() {
  const providersResponse = await props.api.get('/plugin/ClashRuleProvider/rule-providers')
  ruleProviders.value = providersResponse?.data || []
}

async function refreshProxyGroups() {
  const proxyGroupsResponse = await props.api.get('/plugin/ClashRuleProvider/proxy-groups')
  proxyGroups.value = proxyGroupsResponse?.data || []
}

async function refreshExtraProxies() {
  const extraProxiesResponse = await props.api.get('/plugin/ClashRuleProvider/proxies')
  proxies.value = extraProxiesResponse?.data || []
}

async function refreshProxyProviders() {
  const proxyProvidersResponse = await props.api.get('/plugin/ClashRuleProvider/proxy-providers')
  proxyProviders.value = proxyProvidersResponse?.data || []
}

async function refreshDataOf(region: string) {
  switch (region) {
    case 'status':
      return refreshStatus()
    case 'top':
      return refreshTopRules()
    case 'clash-outbounds':
      return refreshOutbounds()
    case 'rule-providers':
      return refreshExtraRuleProviders()
    case 'proxy-groups':
      return refreshProxyGroups()
    case 'proxies':
      return refreshExtraProxies()
    case 'proxy-providers':
      return refreshProxyProviders()
    default:
      throw new Error('Unknown region: ' + region)
  }
}

async function refreshAllRegions(regions: string[]) {
  try {
    await Promise.all(regions.map(refreshDataOf))
  } catch (err: unknown) {
    console.error('获取数据失败:', err)
    if (err instanceof Error) {
      showError(err.message || '获取数据失败')
    }
    status.value = 'error'
  } finally {
    lastUpdated.value = new Date().toLocaleString()
  }
}

// 获取和刷新数据
async function refreshData() {
  loading.value = true
  error.value = false
  errorMsg.value = ''
  try {
    // 并发发送所有独立的请求
    const [
      state,
      response,
      outboundsResponse,
      providersResponse,
      proxyGroupsResponse,
      extraProxiesResponse,
      proxyProvidersResponse
    ] = await Promise.all([
      props.api.get('/plugin/ClashRuleProvider/status'),
      props.api.get('/plugin/ClashRuleProvider/rules/top'),
      props.api.get('/plugin/ClashRuleProvider/clash-outbound'),
      props.api.get('/plugin/ClashRuleProvider/rule-providers'),
      props.api.get('/plugin/ClashRuleProvider/proxy-groups'),
      props.api.get('/plugin/ClashRuleProvider/proxies'),
      props.api.get('/plugin/ClashRuleProvider/proxy-providers')
    ])

    // 处理状态请求的响应
    status.value = state?.data?.state ? 'running' : 'disabled'
    subUrl.value = state?.data?.sub_url || ''

    if (state?.data?.subscription_info) {
      subscriptionsInfo.value = state.data.subscription_info
    }
    bestCloudflareIPs.value = state?.data?.best_cf_ip || []
    rulesetPrefix.value = state?.data?.ruleset_prefix || '📂<='
    geoRules.value = state?.data?.geoRules ?? geoRules.value
    presetIdentifiers.value = state?.data?.preset_identifiers || []
    rules.value = response?.data || []
    customOutbounds.value = outboundsResponse?.data || []
    ruleProviders.value = providersResponse?.data || []
    proxyGroups.value = proxyGroupsResponse?.data || []
    proxies.value = extraProxiesResponse?.data || []
    proxyProviders.value = proxyProvidersResponse?.data || []
    lastUpdated.value = new Date().toLocaleString()
  } catch (err: unknown) {
    console.error('获取数据失败:', err)
    if (err instanceof Error) {
      showError(err.message || '获取数据失败')
    }
    status.value = 'error'
  } finally {
    loading.value = false
  }
}

// 通知主应用切换到配置页面
function notifySwitch() {
  emit('switch')
}

// 通知主应用关闭组件
function notifyClose() {
  emit('close')
}

// 组件挂载时加载数据
onMounted(() => {
  refreshData()
})
</script>
<template>
  <div class="plugin-page">
    <v-card>
      <v-alert v-if="error" v-model="error" type="error" class="mb-4" closable>{{
        errorMsg
      }}</v-alert>
      <v-card-item>
        <v-card-title>
          <v-icon class="mr-2" size="24">
            <img
              :src="`/api/v1/plugin/file/clashruleprovider/dist${MetaLogo}`"
              alt="icon"
              style="width: 100%; height: 100%"
            />
          </v-icon>
          Clash Rule Provider
          <v-chip
            size="small"
            :color="status === 'running' ? 'success' : 'warning'"
            @click="copyPluginLink"
          >
            {{ status }}
          </v-chip>
        </v-card-title>
        <template #append>
          <v-btn icon color="primary" variant="text" @click="notifyClose">
            <v-icon left>mdi-close</v-icon>
          </v-btn>
        </template>
      </v-card-item>
      <v-card-text>
        <v-skeleton-loader v-if="loading" type="card"></v-skeleton-loader>

        <div v-else>
          <!-- Tabs Container -->
          <v-tabs v-model="activeTab" background-color="primary" dark>
            <v-tab>
              <v-icon start>mdi-pin</v-icon>
              置顶规则
            </v-tab>
            <v-tab>
              <v-icon start>mdi-source-branch</v-icon>
              代理组
            </v-tab>
            <v-tab>
              <v-icon start>mdi-rocket-launch</v-icon>
              出站代理
            </v-tab>
            <v-tab>
              <v-icon start>mdi-folder-multiple</v-icon>
              规则集合
            </v-tab>
            <v-tab>
              <v-icon start>mdi-cloud-sync</v-icon>
              订阅状态
            </v-tab>
          </v-tabs>

          <v-window v-model="activeTab">
            <!-- Top Rules Tab -->
            <v-window-item>
              <TopRulesTab
                :rules="sortedRules"
                :api="api"
                :rule-provider-names="ruleProviderNames"
                :geo-rules="geoRules"
                :custom-outbounds="customOutbounds"
                @refresh="refreshAllRegions"
                @show-snackbar="(val) => (snackbar = val)"
                @show-error="showError"
                @edit-visibility="handleEditVisibility"
              />
            </v-window-item>
            <!-- Proxy Groups Tab -->
            <v-window-item>
              <ProxyGroupsTab
                :proxy-groups="proxyGroups"
                :proxy-providers="proxyProviders"
                :custom-outbounds="customOutbounds"
                :api="api"
                @refresh="refreshAllRegions"
                @show-snackbar="(val) => (snackbar = val)"
                @show-error="showError"
                @show-yaml="showYaml"
                @copy-to-clipboard="copyToClipboard"
                @edit-visibility="handleEditVisibility"
              />
            </v-window-item>
            <!-- Proxies Tab -->
            <v-window-item>
              <ProxiesTab
                :proxies="proxies"
                :api="api"
                @refresh="refreshAllRegions"
                @show-snackbar="(val) => (snackbar = val)"
                @show-error="showError"
                @show-yaml="showYaml"
                @copy-to-clipboard="copyToClipboard"
                @edit-visibility="handleEditVisibility"
              />
            </v-window-item>
            <!-- Rule Providers Tab -->
            <v-window-item>
              <RuleProvidersTab
                :rule-providers="ruleProviders"
                :api="api"
                @refresh="refreshAllRegions"
                @show-snackbar="(val) => (snackbar = val)"
                @show-error="showError"
                @show-yaml="showYaml"
                @edit-visibility="handleEditVisibility"
              />
            </v-window-item>
            <!-- Sub Tab -->
            <v-window-item>
              <SubscriptionTab
                :subscriptions-info="subscriptionsInfo"
                :api="api"
                @refresh="refreshAllRegions"
                @show-snackbar="(val) => (snackbar = val)"
                @show-error="showError"
                @copy-to-clipboard="copyToClipboard"
                @switch="notifySwitch"
              />
            </v-window-item>
          </v-window>
        </div>
      </v-card-text>
      <v-expand-transition>
        <div v-if="expand">
          <StatisticsPanel
            :top-rules-count="sortedRules.length"
            :proxy-groups-count="proxyGroups.length"
            :extra-proxies-count="proxies.length"
            :extra-rule-providers-count="ruleProviders.length"
            :geosite-count="geoRules.geosite.length"
            :last-updated="lastUpdated"
          />
        </div>
      </v-expand-transition>
      <v-card-actions>
        <v-btn color="primary" :loading="loading" @click="refreshData">
          <v-icon left>mdi-refresh</v-icon>
          刷新数据
        </v-btn>
        <v-menu v-if="presetIdentifiers.length > 0">
          <template #activator="{ props }">
            <v-btn color="info" v-bind="props">
              <v-icon left>mdi-link-variant</v-icon>
              生成链接
            </v-btn>
          </template>
          <v-list>
            <v-list-item :href="subUrl" target="_blank">
              <template #prepend>
                <v-icon icon="mdi-link-variant"></v-icon>
              </template>
              <v-list-item-title>默认</v-list-item-title>
            </v-list-item>
            <v-list-item
              v-for="id in presetIdentifiers"
              :key="id"
              :href="generateIdentifierUrl(id)"
              target="_blank"
            >
              <template #prepend>
                <v-icon icon="mdi-devices"></v-icon>
              </template>
              <v-list-item-title>{{ id }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
        <v-btn v-else color="info" :href="subUrl" target="_blank">
          <v-icon left>mdi-link-variant</v-icon>
          生成链接
        </v-btn>
        <v-btn color="success" @click="expand = !expand">
          <v-icon left>mdi-chart-bar</v-icon>
          统计信息
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="notifySwitch">
          <v-icon left>mdi-cog</v-icon>
          配置
        </v-btn>
      </v-card-actions>
      <v-snackbar v-model="snackbar.show" :color="snackbar.color" location="bottom" class="mb-2">
        {{ snackbar.message }}
      </v-snackbar>
    </v-card>

    <ShowYamlDialog
      v-if="showYamlDialog"
      :content="displayedYaml"
      @copy-to-clipboard="copyToClipboard"
      @close="showYamlDialog = false"
    >
    </ShowYamlDialog>
    <DataVisibilityDialog
      v-if="visibilityDialogVisible"
      v-model="visibilityDialogVisible"
      :meta="currentVisibilityMeta"
      :endpoint="currentVisibilityEndpoint"
      :region="currentVisibilityRegion"
      :api="api"
      :preset-identifiers="presetIdentifiers"
      @refresh="refreshAllRegions"
      @show-snackbar="(val) => (snackbar = val)"
      @show-error="showError"
      @close="visibilityDialogVisible = false"
    />
  </div>
</template>
<style scoped>
.plugin-page {
  margin: 0 auto;
}
</style>
