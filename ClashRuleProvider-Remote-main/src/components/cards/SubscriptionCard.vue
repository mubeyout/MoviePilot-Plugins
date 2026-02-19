<script setup lang="ts">
import {
  formatBytes,
  formatTimestamp,
  getExpireColor,
  extractDomain,
  getUsedPercentageFloor,
  getUsageColor
} from '@/components/utils'
import { SubscriptionInfo } from '@/components/types'
import { ref } from 'vue'

const props = defineProps<{
  info: SubscriptionInfo
  url: string
  api: any
}>()

const emit = defineEmits<{
  (e: 'show-error', msg: string): void
  (e: 'show-snackbar', value: any): void
  (e: 'refresh', regions: string[]): void
  (e: 'copy-to-clipboard', url: string): void
  (e: 'start-loading'): void
  (e: 'end-loading'): void
}>()

const loading = ref<boolean>(false)

// 更新订阅
async function updateSubscription() {
  loading.value = true
  emit('start-loading')
  try {
    await props.api.put('plugin/ClashRuleProvider/refresh', {
      url: props.url
    })
    // 显示成功提示
    emit('show-snackbar', {
      show: true,
      message: '订阅更新成功',
      color: 'success'
    })
    emit('refresh', [
      'status',
      'clash-outbounds',
      'rule-providers',
      'proxy-groups',
      'proxies',
      'proxy-providers'
    ])
  } catch (err: unknown) {
    if (err instanceof Error) emit('show-error', '订阅更新失败: ' + (err.message || '未知错误'))
  } finally {
    loading.value = false
    emit('end-loading')
  }
}

async function toggleSubscription(val: boolean) {
  emit('start-loading')
  try {
    await props.api.post('plugin/ClashRuleProvider/subscription-info', {
      url: props.url,
      enabled: val
    })
    // 显示成功提示
    emit('show-snackbar', {
      show: true,
      message: '设置成功',
      color: 'success'
    })
    emit('refresh', ['status'])
  } catch (err: unknown) {
    if (err instanceof Error) emit('show-error', '设置自动更新失败: ' + (err.message || '未知错误'))
    emit('refresh', ['status'])
  } finally {
    emit('end-loading')
  }
}
</script>
<template>
  <v-card class="subscription-card mb-4" elevation="0" border>
    <div class="card-header pa-4">
      <div class="d-flex align-center overflow-hidden">
        <v-avatar color="primary" variant="tonal" rounded="lg" class="mr-3">
          <v-icon>mdi-rss</v-icon>
        </v-avatar>
        <div class="d-flex flex-column overflow-hidden">
          <div class="text-subtitle-1 font-weight-bold text-truncate">
            {{ extractDomain(url) }}
          </div>
          <div class="text-caption text-medium-emphasis text-truncate">
            {{ url }}
          </div>
        </div>
      </div>

      <v-spacer></v-spacer>
    </div>

    <v-divider></v-divider>

    <v-card-text class="pa-4">
      <div class="d-flex flex-wrap gap-2 mb-4" style="gap: 8px">
        <v-chip
          v-if="info.proxy_num != null"
          size="small"
          color="primary"
          variant="flat"
          class="font-weight-medium"
        >
          <v-icon start size="small">mdi-server-network</v-icon>
          {{ info.proxy_num }} 节点
        </v-chip>
        <v-chip v-if="info.last_update" size="small" color="secondary" variant="tonal">
          <v-icon start size="small">mdi-clock-outline</v-icon>
          {{ formatTimestamp(info.last_update) }}
        </v-chip>
        <v-chip
          v-if="info.expire"
          size="small"
          :color="getExpireColor(info.expire)"
          variant="tonal"
        >
          <v-icon start size="small">mdi-calendar-clock</v-icon>
          到期：{{ formatTimestamp(info.expire) }}
        </v-chip>
      </div>

      <div class="stats-grid mb-4">
        <div class="stat-item">
          <div class="text-caption text-medium-emphasis">已用</div>
          <div class="text-body-2 font-weight-bold">
            {{ formatBytes(info.download + info.upload) }}
          </div>
        </div>
        <div class="stat-item text-right">
          <div class="text-caption text-medium-emphasis">剩余</div>
          <div class="text-body-2 font-weight-bold">
            {{ formatBytes(info.total - info.download - info.upload) }}
          </div>
        </div>
      </div>

      <v-progress-linear
        :model-value="getUsedPercentageFloor(info)"
        :color="getUsageColor(getUsedPercentageFloor(info))"
        height="8"
        rounded
        class="mb-2"
      ></v-progress-linear>

      <div class="d-flex justify-space-between text-caption text-medium-emphasis">
        <span>↓ {{ formatBytes(info.download) }}</span>
        <span>↑ {{ formatBytes(info.upload) }}</span>
        <span>Total: {{ formatBytes(info.total) }}</span>
      </div>
    </v-card-text>

    <v-divider></v-divider>

    <div class="card-actions px-4 py-2 d-flex align-center bg-surface-variant-lighten">
      <v-btn
        icon
        size="small"
        variant="text"
        color="primary"
        :loading="loading"
        @click="updateSubscription"
      >
        <v-icon>mdi-refresh</v-icon>
        <v-tooltip activator="parent" location="top">刷新</v-tooltip>
      </v-btn>

      <v-spacer></v-spacer>

      <div class="d-flex align-center">
        <span class="text-caption mr-2 text-medium-emphasis">自动更新</span>
        <v-switch
          :model-value="info.enabled"
          hide-details
          density="compact"
          color="primary"
          inset
          @update:model-value="toggleSubscription"
        ></v-switch>
      </div>
    </div>
  </v-card>
</template>
<style scoped>
.subscription-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.subscription-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 25px 0 rgba(0, 0, 0, 0.1);
  border-color: rgb(var(--v-theme-primary));
}

.card-header {
  background: rgba(var(--v-theme-surface-variant), 0.05);
}

.bg-surface-variant-lighten {
  background: rgba(var(--v-theme-surface-variant), 0.02);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
</style>
