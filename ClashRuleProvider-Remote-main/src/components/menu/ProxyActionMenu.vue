<script setup lang="ts">
import { PropType } from 'vue'
import { ProxyData } from '@/components/types'
import { isManual, isInvalid } from '@/components/utils'

defineProps({
  proxy: {
    type: Object as PropType<ProxyData>,
    required: true
  }
})

const emit = defineEmits<{
  (e: 'showYaml'): void
  (e: 'edit'): void
  (e: 'delete'): void
  (e: 'deletePatch'): void
  (e: 'changeStatus', disabled: boolean): void
  (e: 'copyToClipboard', text: string): void
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
        v-if="isManual(proxy.meta.source)"
        @click="emit('changeStatus', !proxy.meta.disabled)"
      >
        <template #prepend>
          <v-icon size="small" :color="proxy.meta.disabled ? 'success' : 'grey'">
            {{ proxy.meta.disabled ? 'mdi-play-circle-outline' : 'mdi-stop-circle-outline' }}
          </v-icon>
        </template>
        <v-list-item-title>{{ proxy.meta.disabled ? '启用' : '禁用' }}</v-list-item-title>
      </v-list-item>

      <v-list-item @click="emit('showYaml')">
        <template #prepend>
          <v-icon size="small" color="info">mdi-code-json</v-icon>
        </template>
        <v-list-item-title>查看</v-list-item-title>
      </v-list-item>

      <v-list-item @click="emit('edit')">
        <template #prepend>
          <v-icon size="small" color="primary">mdi-file-edit-outline</v-icon>
        </template>
        <v-list-item-title>编辑</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="isManual(proxy.meta.source)" @click="emit('editVisibility')">
        <template #prepend>
          <v-icon size="small" color="warning">mdi-eye-off-outline</v-icon>
        </template>
        <v-list-item-title>隐藏</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="proxy.v2ray_link" @click="emit('copyToClipboard', proxy.v2ray_link)">
        <template #prepend>
          <v-icon size="small" color="secondary">mdi-link</v-icon>
        </template>
        <v-list-item-title>复制链接</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="proxy.meta.patched" @click="emit('deletePatch')">
        <template #prepend>
          <v-icon size="small" color="error">mdi-close-box-outline</v-icon>
        </template>
        <v-list-item-title>删除补丁</v-list-item-title>
      </v-list-item>

      <v-list-item
        :disabled="!(isManual(proxy.meta.source) || isInvalid(proxy.meta.source))"
        @click="emit('delete')"
      >
        <template #prepend>
          <v-icon size="small" color="error">mdi-trash-can-outline</v-icon>
        </template>
        <v-list-item-title>删除</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<style scoped></style>
