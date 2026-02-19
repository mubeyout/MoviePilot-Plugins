<script setup lang="ts">
import { PropType } from 'vue'
import { ProxyGroupData } from '@/components/types'
import { isManual, isRegion } from '@/components/utils'

defineProps({
  proxyGroup: {
    type: Object as PropType<ProxyGroupData>,
    required: true
  }
})

const emit = defineEmits<{
  (e: 'showYaml'): void
  (e: 'edit'): void
  (e: 'delete'): void
  (e: 'deletePatch'): void
  (e: 'changeStatus', disabled: boolean): void
  (e: 'editVisibility'): void
}>()
</script>

<template>
  <v-menu min-width="120">
    <template #activator="{ props }">
      <v-btn color="secondary" icon size="small" variant="text" v-bind="props">
        <v-icon>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>
    <v-list density="compact">
      <v-list-item
        v-if="isManual(proxyGroup.meta.source)"
        @click="emit('changeStatus', !proxyGroup.meta.disabled)"
      >
        <template #prepend>
          <v-icon size="small" :color="proxyGroup.meta.disabled ? 'success' : 'grey'">
            {{ proxyGroup.meta.disabled ? 'mdi-play-circle-outline' : 'mdi-stop-circle-outline' }}
          </v-icon>
        </template>
        <v-list-item-title>{{ proxyGroup.meta.disabled ? '启用' : '禁用' }}</v-list-item-title>
      </v-list-item>

      <v-list-item @click="emit('showYaml')">
        <template #prepend>
          <v-icon size="small" color="info">mdi-code-json</v-icon>
        </template>
        <v-list-item-title>查看</v-list-item-title>
      </v-list-item>

      <v-list-item
        v-if="isManual(proxyGroup.meta.source) || isRegion(proxyGroup.meta.source)"
        @click="emit('edit')"
      >
        <template #prepend>
          <v-icon size="small" color="primary">mdi-file-edit-outline</v-icon>
        </template>
        <v-list-item-title>编辑</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="isManual(proxyGroup.meta.source)" @click="emit('editVisibility')">
        <template #prepend>
          <v-icon size="small" color="warning">mdi-eye-off-outline</v-icon>
        </template>
        <v-list-item-title>隐藏</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="proxyGroup.meta.patched" @click="emit('deletePatch')">
        <template #prepend>
          <v-icon size="small" color="error">mdi-close-box-outline</v-icon>
        </template>
        <v-list-item-title>删除补丁</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="isManual(proxyGroup.meta.source)" @click="emit('delete')">
        <template #prepend>
          <v-icon size="small" color="error">mdi-trash-can-outline</v-icon>
        </template>
        <v-list-item-title>删除</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<style scoped></style>
