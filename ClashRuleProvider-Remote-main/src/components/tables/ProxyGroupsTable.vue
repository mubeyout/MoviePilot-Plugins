<script setup lang="ts">
import { PropType, ref } from 'vue'
import { ProxyGroupData } from '@/components/types'
import { itemsPerPageOptions } from '@/components/constants'
import { getProxyGroupTypeColor, getSourceColor } from '@/components/utils'
import ProxyGroupActionMenu from '@/components/menu/ProxyGroupActionMenu.vue'

defineProps({
  proxyGroups: {
    type: Array as PropType<ProxyGroupData[]>,
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
  (e: 'copyToClipboard', content: string): void
  (e: 'showYaml', obj: any): void
  (e: 'editProxyGroup', name: string): void
  (e: 'deleteProxyGroup', name: string): void
  (e: 'deletePatch', name: string): void
  (e: 'changeStatus', name: string, disabled: boolean): void
  (e: 'editVisibility', name: string): void
}>()

const proxyGroupHeaders = ref([
  { title: '名称', key: 'name', sortable: true },
  { title: '类型', key: 'type', sortable: false },
  { title: '来源', key: 'source', sortable: false },
  { title: '', key: 'status', sortable: false, width: '1.5rem' },
  { title: '', key: 'actions', sortable: false, width: '1rem' }
])
</script>

<template>
  <v-data-table
    class="px-4"
    :headers="proxyGroupHeaders"
    :search="search"
    :items="proxyGroups"
    :page="page"
    :items-per-page="itemsPerPage"
    :items-per-page-options="itemsPerPageOptions"
    density="compact"
    hide-default-footer
    fixed-header
    item-key="name"
  >
    <template #item.name="{ item }">
      <v-chip size="small" pill color="secondary">{{ item.data.name }}</v-chip>
    </template>

    <template #item.type="{ item }">
      <v-chip :color="getProxyGroupTypeColor(item.data.type)" size="small" label variant="tonal">
        {{ item.data.type }}
      </v-chip>
    </template>

    <template #item.source="{ item }">
      <v-chip size="small" :color="getSourceColor(item.meta.source)" variant="outlined">{{
        item.meta.source
      }}</v-chip>
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
        <v-tooltip v-if="item.meta.patched" text="已应用补丁" location="top">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="info"> mdi-auto-fix </v-icon>
          </template>
        </v-tooltip>
      </div>
    </template>

    <template #item.actions="{ item }">
      <ProxyGroupActionMenu
        :proxy-group="item"
        @change-status="(disabled) => emit('changeStatus', item.data.name, disabled)"
        @show-yaml="emit('showYaml', item.data)"
        @edit="emit('editProxyGroup', item.data.name)"
        @delete="emit('deleteProxyGroup', item.data.name)"
        @delete-patch="emit('deletePatch', item.data.name)"
        @edit-visibility="emit('editVisibility', item.data.name)"
      />
    </template>
  </v-data-table>
</template>

<style scoped></style>
