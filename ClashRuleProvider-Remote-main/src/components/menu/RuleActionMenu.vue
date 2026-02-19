<script setup lang="ts">
import { PropType } from 'vue'
import { RuleData } from '@/components/types'
import { isSystemRule } from '@/components/utils'

defineProps({
  rule: {
    type: Object as PropType<RuleData>,
    required: true
  },
  hideVisibility: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits<{
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
      <v-tooltip v-if="isSystemRule(rule)" activator="parent" location="top">
        根据规则集自动添加
      </v-tooltip>
    </template>
    <v-list density="compact">
      <v-list-item @click="emit('changeStatus', !rule.meta?.disabled)">
        <template #prepend>
          <v-icon size="small" :color="rule.meta?.disabled ? 'success' : 'grey'">
            {{ rule.meta?.disabled ? 'mdi-play-circle-outline' : 'mdi-stop-circle-outline' }}
          </v-icon>
        </template>
        <v-list-item-title>{{ rule.meta?.disabled ? '启用' : '禁用' }}</v-list-item-title>
      </v-list-item>
      <v-list-item v-if="!isSystemRule(rule)" @click="emit('edit')">
        <template #prepend>
          <v-icon size="small" color="primary">mdi-file-edit-outline</v-icon>
        </template>
        <v-list-item-title>编辑</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="!hideVisibility" @click="emit('editVisibility')">
        <template #prepend>
          <v-icon size="small" color="warning">mdi-eye-off-outline</v-icon>
        </template>
        <v-list-item-title>隐藏</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="!isSystemRule(rule)" @click="emit('delete')">
        <template #prepend>
          <v-icon size="small" color="error">mdi-trash-can-outline</v-icon>
        </template>
        <v-list-item-title>删除</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<style scoped></style>
