<script setup lang="ts">
import { reactive, onMounted, onUnmounted, ref } from 'vue'
import MetaLogo from '@/assets/Meta.png'

const props = defineProps({
  config: {
    type: Object,
    default: () => ({})
  },
  allowRefresh: {
    type: Boolean,
    default: true
  },
  api: {
    type: Object,
    required: true
  }
})

const defaultConfig = {
  title: 'Clash Info',
  clash_available: false,
  secret: ''
}

const componentConfig: any = reactive({ ...defaultConfig })

const clashInfo = ref<Record<string, any>>({
  version: { meta: false, version: 'unknown' },
  status: 'not connected',
  configs: {},
  rules: {},
  proxies: [],
  'rule-providers': {}
})

let refreshTimer: number | null = null

async function fetchClashData(
  endpoint: string,
  dataKey: 'version' | 'configs' | 'rules' | 'rule-providers'
) {
  try {
    const data = await props.api.get(`plugin/ClashRuleProvider/clash/proxy/${endpoint}`)
    if (!data) {
      clashInfo.value.status = 'not connected'
    }
    clashInfo.value.status = 'connected'
    clashInfo.value[dataKey] = data
  } catch (error) {
    clashInfo.value.status = 'not connected'
  }
}

async function fetchAllClashData() {
  await Promise.all([
    fetchClashData('version', 'version'),
    fetchClashData('configs', 'configs'),
    fetchClashData('rules', 'rules'),
    fetchClashData('providers/rules', 'rule-providers')
  ])
}

function setupRefreshTimer() {
  if (props.allowRefresh) {
    refreshTimer = setInterval(() => {
      fetchAllClashData()
    }, 30000)
  }
}

onMounted(() => {
  if (props.config?.attrs) {
    Object.keys(props.config.attrs).forEach((key) => {
      if (key in componentConfig) {
        componentConfig[key] = props.config.attrs[key]
      }
    })
  }

  if (componentConfig.clash_available) {
    fetchAllClashData()
    setupRefreshTimer()
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>
<template>
  <v-card class="h-100">
    <v-card-item>
      <v-card-title>{{ config?.attrs?.title || 'Clash Info' }}</v-card-title>
    </v-card-item>
    <v-card-text class="h-100 d-flex flex-column pt-4">
      <div class="d-flex flex-column">
        <div class="d-flex align-center text-center">
          <v-img
            v-if="clashInfo.version.meta"
            :src="`/api/v1/plugin/file/clashruleprovider/dist${MetaLogo}`"
            alt="Logo"
            max-height="48"
            contain
          ></v-img>
          <v-img
            v-else
            src="/api/v1/system/img/1?cache=1&imgurl=https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/refs/heads/main/icons/Clash_A.png"
            alt="Logo"
            max-height="48"
            contain
          ></v-img>
        </div>

        <div class="d-flex flex-column flex-grow-1 justify-space-between gap-4 mt-8">
          <div class="d-flex justify-space-between text-body-2 border-b pb-1">
            <span>连接状态</span>
            <v-chip size="small" :color="clashInfo.status === 'connected' ? 'success' : 'grey'">
              {{ clashInfo.status }}
            </v-chip>
          </div>
          <div class="d-flex justify-space-between text-body-2 border-b pb-1">
            <span>内核版本</span>
            <span>{{ clashInfo.version.version }}</span>
          </div>
          <div class="d-flex justify-space-between text-body-2 border-b pb-1">
            <span>混合代理端口</span>
            <span>{{ clashInfo.configs?.['mixed-port'] || 0 }}</span>
          </div>
          <div class="d-flex justify-space-between text-body-2 border-b pb-1">
            <span>规则数量</span>
            <span>{{ clashInfo.rules?.rules.length }}</span>
          </div>
          <div class="d-flex justify-space-between text-body-2">
            <span>规则集数量</span>
            <span
              >{{ Object.keys(clashInfo?.['rule-providers']?.['providers'] || {}).length || 0 }}
            </span>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>
