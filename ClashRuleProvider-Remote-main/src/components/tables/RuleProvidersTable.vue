<script setup lang="ts">
import { PropType, ref } from 'vue'
import { RuleProviderData } from '@/components/types'
import { itemsPerPageOptions } from '@/components/constants'
import { isManual, getBehaviorColor, getSourceColor, getFormatColor } from '@/components/utils'
import RuleProviderActionMenu from '@/components/menu/RuleProviderActionMenu.vue'

defineProps({
  ruleProviders: {
    type: Array as PropType<RuleProviderData[]>,
    required: true
  },
  page: {
    type: Number,
    required: true
  },
  itemsPerPage: {
    type: Number,
    required: true
  },
  search: String
})

const emit = defineEmits<{
  (e: 'editRuleProvider', name: string): void
  (e: 'deleteRuleProvider', name: string): void
  (e: 'showYaml', obj: any): void
  (e: 'changeStatus', name: string, disabled: boolean): void
  (e: 'editVisibility', name: string): void
}>()

const headersRuleProviders = ref([
  { title: '名称', key: 'name', sortable: true },
  { title: '类型', key: 'type', sortable: true },
  { title: '行为', key: 'behavior', sortable: false },
  { title: '格式', key: 'format', sortable: false },
  { title: '来源', key: 'source', sortable: false },
  { title: '', key: 'status', sortable: false, width: '1rem' },
  { title: '', key: 'actions', sortable: false, width: '1rem' }
])
</script>

<template>
  <v-data-table
    :headers="headersRuleProviders"
    :items="ruleProviders"
    :search="search"
    :page="page"
    :items-per-page="itemsPerPage"
    :items-per-page-options="itemsPerPageOptions"
    item-key="name"
    class="px-4"
    density="compact"
    hide-default-footer
    fixed-header
  >
    <template #item.name="{ item }">
      <v-chip size="small" pill color="secondary">{{ item.name }}</v-chip>
    </template>
    <template #item.type="{ item }">
      <v-chip size="small" label variant="tonal" color="primary">
        {{ item.data.type }}
      </v-chip>
    </template>

    <template #item.behavior="{ item }">
      <v-chip
        v-if="item.data?.behavior"
        :color="getBehaviorColor(item.data.behavior)"
        size="small"
        label
        variant="tonal"
      >
        {{ item.data.behavior }}
      </v-chip>
    </template>

    <template #item.format="{ item }">
      <v-chip :color="getFormatColor(item.data.format)" size="small" label variant="tonal">
        {{ item.data.format }}
      </v-chip>
    </template>

    <template #item.source="{ item }">
      <v-chip :color="getSourceColor(item.meta.source)" size="small" variant="outlined">
        {{ item.meta.source }}
      </v-chip>
    </template>

    <template #item.status="{ item }">
      <div class="d-flex align-center">
        <v-icon :color="item.meta.disabled ? 'grey' : 'success'" class="mr-1">
          {{ item.meta.disabled ? 'mdi-close-circle-outline' : 'mdi-check-circle-outline' }}
        </v-icon>
        <v-tooltip
          v-if="item.meta.invisible_to && item.meta.invisible_to.length > 0"
          text="已配置可见性限制"
          location="top"
        >
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="warning"> mdi-eye-off-outline </v-icon>
          </template>
        </v-tooltip>
      </div>
    </template>

    <template #item.actions="{ item }">
      <RuleProviderActionMenu
        :rule-provider="item"
        @change-status="(disabled) => emit('changeStatus', item.name, disabled)"
        @edit="emit('editRuleProvider', item.name)"
        @show-yaml="emit('showYaml', item.data)"
        @delete="emit('deleteRuleProvider', item.name)"
        @edit-visibility="emit('editVisibility', item.name)"
      />
      <v-tooltip v-if="!isManual(item.meta.source)" activator="parent" location="top">
        非手动添加
      </v-tooltip>
    </template>
  </v-data-table>
</template>

<style scoped></style>
