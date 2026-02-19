<script setup lang="ts">
import TrafficStatsCard from '@/components/cards/TrafficStatsCard.vue'
import ClashInfoCard from '@/components/cards/ClashInfoCard.vue'

defineProps({
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
</script>

<template>
  <div class="dashboard-widget">
    <!-- 仪表板内容 -->
    <TrafficStatsCard
      v-if="config?.key === 'traffic_stats'"
      :config="config"
      :allow-refresh="allowRefresh"
    />
    <ClashInfoCard v-else :config="config" :allow-refresh="allowRefresh" :api="api" />
  </div>
</template>

<style scoped>
.dashboard-widget {
  font-family: 'Inter', sans-serif;
}
</style>
