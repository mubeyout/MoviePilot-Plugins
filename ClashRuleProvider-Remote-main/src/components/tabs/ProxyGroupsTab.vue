<script setup lang="ts">
import { computed, ref } from 'vue'
import ProxyGroupsTable from '@/components/tables/ProxyGroupsTable.vue'
import ProxyGroupCard from '@/components/cards/ProxyGroupCard.vue'
import ProxyGroupsDialog from '@/components/dialog/ProxyGroupsDialog.vue'
import ImportProxyGroupsDialog from '@/components/dialog/ImportProxyGroupsDialog.vue'
import { itemsPerPageOptions } from '@/components/constants'
import { pageTitle } from '@/components/utils'
import { Metadata, ProxyGroupData, ProxyProviderData } from '@/components/types'

const props = defineProps<{
  proxyGroups: ProxyGroupData[]
  proxyProviders: ProxyProviderData[]
  customOutbounds: string[]
  api: any
}>()

const emit = defineEmits<{
  (e: 'refresh', regions: string[]): void
  (e: 'show-snackbar', value: any): void
  (e: 'show-error', msg: string): void
  (e: 'show-yaml', obj: any): void
  (e: 'copy-to-clipboard', text: string): void
  (e: 'edit-visibility', meta: Metadata, endpoint: string, region: string): void
}>()

const searchProxyGroups = ref('')
const pageProxyGroup = ref(1)
const itemsPerPageProxyGroup = ref(10)
const loading = ref(false)

// Dialog State
const proxyGroupDialogVisible = ref(false)
const importProxyGroupsDialogVisible = ref(false)
const editingProxyGroupName = ref<string | null>(null)
const currentProxyGroup = ref<ProxyGroupData | null>(null)

const filteredProxyGroups = computed(() => {
  if (!searchProxyGroups.value) return props.proxyGroups
  const keyword = searchProxyGroups.value.toLowerCase()
  return props.proxyGroups.filter((item) =>
    Object.values(item).some((val) => String(val).toLowerCase().includes(keyword))
  )
})

const paginatedProxyGroups = computed(() => {
  const start = (pageProxyGroup.value - 1) * itemsPerPageProxyGroup.value
  const end = start + itemsPerPageProxyGroup.value
  return filteredProxyGroups.value.slice(start, end)
})

const pageCountProxyGroups = computed(() => {
  if (itemsPerPageProxyGroup.value === -1) {
    return 1
  }
  return Math.ceil(filteredProxyGroups.value.length / itemsPerPageProxyGroup.value)
})

// Actions
function openAddProxyGroupDialog() {
  editingProxyGroupName.value = null
  currentProxyGroup.value = null
  proxyGroupDialogVisible.value = true
}

function openImportProxyGroupsDialog() {
  importProxyGroupsDialogVisible.value = true
}

function editProxyGroup(name: string) {
  const proxyGroupData = props.proxyGroups.find((p) => p.data.name === name)
  if (proxyGroupData) {
    editingProxyGroupName.value = name
    currentProxyGroup.value = { ...proxyGroupData }
    proxyGroupDialogVisible.value = true
  }
}

async function deleteProxyGroup(name: string) {
  loading.value = true
  try {
    const n = encodeURIComponent(name)
    await props.api.delete(`/plugin/ClashRuleProvider/proxy-groups/${n}`)
    emit('refresh', ['proxy-groups', 'clash-outbounds'])
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', err.message || '删除规则失败')
    }
  } finally {
    loading.value = false
  }
}

async function deletePatch(name: string) {
  loading.value = true
  try {
    const n = encodeURIComponent(name)
    await props.api.delete(`/plugin/ClashRuleProvider/proxy-groups/${n}/patch`)
    emit('refresh', ['proxy-groups', 'clash-outbounds'])
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', err.message || '删除补丁失败')
    }
  } finally {
    loading.value = false
  }
}

async function handleStatusChange(name: string, disabled: boolean) {
  loading.value = true
  try {
    const group = props.proxyGroups.find((g) => g.data.name === name)
    if (!group) {
      emit('show-error', 'Proxy group not found')
      return
    }
    const n = encodeURIComponent(name)
    // Send full metadata with updated disabled status
    const newMeta = { ...group.meta, disabled: disabled }
    await props.api.patch(`/plugin/ClashRuleProvider/proxy-groups/${n}/meta`, newMeta)
    emit('refresh', ['proxy-groups', 'clash-outbounds'])
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', err.message || '更新代理组状态失败')
    }
  } finally {
    loading.value = false
  }
}

function editVisibility(name: string) {
  const group = props.proxyGroups.find((g) => g.data.name === name)
  if (!group) {
    emit('show-error', 'Proxy group not found')
    return
  }
  const n = encodeURIComponent(name)
  emit(
    'edit-visibility',
    group.meta,
    `/plugin/ClashRuleProvider/proxy-groups/${n}/meta`,
    'proxy-groups'
  )
}

function closeProxyGroupsDialog() {
  currentProxyGroup.value = null
  proxyGroupDialogVisible.value = false
}
</script>
<template>
  <div class="mb-2 position-relative">
    <v-overlay v-model="loading" contained class="align-center justify-center">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
    </v-overlay>
    <div class="pa-4">
      <v-row align="center" no-gutters>
        <v-col cols="10" sm="6" class="d-flex justify-start">
          <v-text-field
            v-model="searchProxyGroups"
            label="搜索代理组"
            clearable
            density="compact"
            variant="solo-filled"
            hide-details
            class="search-field"
            prepend-inner-icon="mdi-magnify"
            flat
            rounded="pill"
            single-line
            :disabled="loading"
          ></v-text-field>
        </v-col>
        <v-col cols="2" sm="6" class="d-flex justify-end">
          <v-btn-group variant="outlined" rounded>
            <v-btn icon="mdi-import" :disabled="loading" @click="openImportProxyGroupsDialog"> </v-btn>
            <v-btn icon="mdi-plus" :disabled="loading" @click="openAddProxyGroupDialog"> </v-btn>
          </v-btn-group>
        </v-col>
      </v-row>
    </div>

    <!-- 桌面端表格 -->

    <div class="d-none d-sm-flex clash-data-table">
      <ProxyGroupsTable
        :items-per-page="itemsPerPageProxyGroup"
        :page="pageProxyGroup"
        :proxy-groups="proxyGroups"
        :search="searchProxyGroups"
        @copy-to-clipboard="(t) => emit('copy-to-clipboard', t)"
        @show-yaml="(o) => emit('show-yaml', o)"
        @edit-proxy-group="editProxyGroup"
        @delete-proxy-group="deleteProxyGroup"
        @delete-patch="deletePatch"
        @change-status="handleStatusChange"
        @edit-visibility="editVisibility"
      ></ProxyGroupsTable>
    </div>
    <!-- 移动端卡片 -->
    <div class="d-sm-none">
      <v-row>
        <v-col v-for="item in paginatedProxyGroups" :key="item.data.name" cols="12">
          <ProxyGroupCard
            :proxy-group-data="item"
            @edit-proxy-group="editProxyGroup"
            @delete-proxy-group="deleteProxyGroup"
            @delete-patch="deletePatch"
            @show-yaml="(o) => emit('show-yaml', o)"
            @change-status="handleStatusChange"
            @edit-visibility="editVisibility"
          ></ProxyGroupCard>
        </v-col>
      </v-row>
    </div>
    <div class="pa-4" style="min-height: 4rem">
      <v-row align="center" no-gutters>
        <v-col cols="2" md="1"> </v-col>
        <v-col cols="8" md="10" class="d-flex justify-center">
          <v-pagination
            v-model="pageProxyGroup"
            :length="pageCountProxyGroups"
            total-visible="5"
            class="d-none d-sm-flex my-0"
            rounded="circle"
            :disabled="loading"
          />

          <v-pagination
            v-model="pageProxyGroup"
            :length="pageCountProxyGroups"
            total-visible="0"
            class="d-sm-none my-0"
            rounded="circle"
            :disabled="loading"
          />
        </v-col>
        <v-col cols="2" md="1" class="d-flex justify-end">
          <v-menu>
            <template #activator="{ props }">
              <v-btn v-bind="props" icon rounded="circle" variant="tonal" :disabled="loading">
                {{ pageTitle(itemsPerPageProxyGroup) }}
              </v-btn>
            </template>
            <v-list>
              <v-list-item
                v-for="(item, index) in itemsPerPageOptions"
                :key="index"
                :value="item.value"
                @click="itemsPerPageProxyGroup = item.value"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
      </v-row>
    </div>
    <v-divider></v-divider>
    <!-- Add ProxyGroup Dialog -->
    <ProxyGroupsDialog
      v-if="proxyGroupDialogVisible"
      v-model="proxyGroupDialogVisible"
      :initial-value="currentProxyGroup"
      :is-adding="editingProxyGroupName === null"
      :proxy-providers="proxyProviders"
      :custom-outbounds="customOutbounds"
      :api="api"
      @close="closeProxyGroupsDialog"
      @refresh="emit('refresh', ['clash-outbounds', 'proxy-groups'])"
      @show-snackbar="(val) => emit('show-snackbar', val)"
      @show-error="(msg) => emit('show-error', msg)"
    ></ProxyGroupsDialog>
    <!-- Import ProxyGroups Dialog -->
    <ImportProxyGroupsDialog
      v-model="importProxyGroupsDialogVisible"
      :api="api"
      @refresh="emit('refresh', ['clash-outbounds', 'proxy-groups'])"
      @show-snackbar="(val) => emit('show-snackbar', val)"
      @show-error="(msg) => emit('show-error', msg)"
    ></ImportProxyGroupsDialog>
  </div>
</template>

<style scoped></style>
