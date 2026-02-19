<template>
  <v-row dense>
    <v-col cols="6" md="3">
      <v-card class="pa-4 d-flex flex-column align-center" rounded="xl">
        <v-icon size="40" color="info">mdi-pin</v-icon>
        <div class="text-h6 mt-2 font-weight-bold">{{ topRulesCount }}</div>
        <div class="text-subtitle-2 grey--text">置顶规则</div>
      </v-card>
    </v-col>
    <v-col cols="6" md="3">
      <v-card class="pa-4 d-flex flex-column align-center" rounded="xl">
        <v-icon size="40" color="success">mdi-source-branch</v-icon>
        <div class="text-h6 mt-2 font-weight-bold">{{ proxyGroupsCount }}</div>
        <div class="text-subtitle-2 grey--text">代理组</div>
      </v-card>
    </v-col>
    <v-col cols="6" md="3">
      <v-card class="pa-4 d-flex flex-column align-center" rounded="xl">
        <v-icon size="40" color="error">mdi-rocket-launch</v-icon>
        <div class="text-h6 mt-2 font-weight-bold">{{ extraProxiesCount }}</div>
        <div class="text-subtitle-2 grey--text">出站代理</div>
      </v-card>
    </v-col>
    <v-col cols="6" md="3">
      <v-card class="pa-4 d-flex flex-column align-center" rounded="xl">
        <v-icon size="40" color="warning">mdi-folder-multiple</v-icon>
        <div class="text-h6 mt-2 font-weight-bold">{{ extraRuleProvidersCount }}</div>
        <div class="text-subtitle-2 grey--text">规则集合</div>
      </v-card>
    </v-col>
    <v-col cols="6" md="3">
      <v-card class="pa-4 d-flex flex-column align-center" rounded="xl">
        <v-icon size="40" color="info">mdi-earth</v-icon>
        <div class="text-h6 mt-2 font-weight-bold">{{ geositeCount }}</div>
        <div class="text-subtitle-2 grey--text">Geosite</div>
      </v-card>
    </v-col>
    <v-col cols="6" md="3">
      <v-card class="pa-4 d-flex flex-column align-center" rounded="xl">
        <v-icon size="40" color="success">mdi-clock-time-four-outline</v-icon>
        <div class="text-h6 mt-2 font-weight-bold">{{ lastUpdated }}</div>
        <div class="text-subtitle-2 grey--text">最后更新</div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
defineProps<{
  topRulesCount: number
  proxyGroupsCount: number
  extraProxiesCount: number
  extraRuleProvidersCount: number
  geositeCount: number
  lastUpdated: string
}>()
</script>
