<script setup lang="ts">
import { PropType } from 'vue'
import { RuleProviderData } from '@/components/types'
import { isManual } from '@/components/utils'

defineProps({
  ruleProvider: {
    type: Object as PropType<RuleProviderData>,
    required: true
  }
})

const emit = defineEmits<{
  (e: 'showYaml'): void
  (e: 'edit'): void
  (e: 'delete'): void
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
        v-if="isManual(ruleProvider.meta.source)"
        @click="emit('changeStatus', !ruleProvider.meta.disabled)"
      >
        <template #prepend>
          <v-icon size="small" :color="ruleProvider.meta.disabled ? 'success' : 'grey'">
            {{ ruleProvider.meta.disabled ? 'mdi-play-circle-outline' : 'mdi-stop-circle-outline' }}
          </v-icon>
        </template>
        <v-list-item-title>{{ ruleProvider.meta.disabled ? '启用' : '禁用' }}</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="isManual(ruleProvider.meta.source)" @click="emit('edit')">
        <template #prepend>
          <v-icon size="small" color="primary">mdi-file-edit-outline</v-icon>
        </template>
        <v-list-item-title>编辑</v-list-item-title>
      </v-list-item>

      <v-list-item @click="emit('showYaml')">
        <template #prepend>
          <v-icon size="small" color="info">mdi-code-json</v-icon>
        </template>
        <v-list-item-title>查看</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="isManual(ruleProvider.meta.source)" @click="emit('editVisibility')">
        <template #prepend>
          <v-icon size="small" color="warning">mdi-eye-off-outline</v-icon>
        </template>
        <v-list-item-title>隐藏</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="isManual(ruleProvider.meta.source)" @click="emit('delete')">
        <template #prepend>
          <v-icon size="small" color="error">mdi-trash-can-outline</v-icon>
        </template>
        <v-list-item-title>删除</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<style scoped></style>
