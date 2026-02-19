<script setup lang="ts">
import { ref, computed, toRaw } from 'vue'
import { Metadata, RuleProviderData } from '@/components/types'
import RuleProvidersTable from '@/components/tables/RuleProvidersTable.vue'
import RuleProviderCard from '@/components/cards/RuleProviderCard.vue'
import RuleProviderDialog from '@/components/dialog/RuleProviderDialog.vue'
import ImportRuleProvidersDialog from '@/components/dialog/ImportRuleProvidersDialog.vue'
import { itemsPerPageOptions } from '@/components/constants'
import { pageTitle } from '@/components/utils'

const props = defineProps<{
  ruleProviders: RuleProviderData[]
  api: any
}>()

const emit = defineEmits<{
  (e: 'refresh', regions: string[]): void
  (e: 'show-snackbar', value: any): void
  (e: 'show-error', msg: string): void
  (e: 'show-yaml', obj: any): void
  (e: 'edit-visibility', meta: Metadata, endpoint: string, region: string): void
}>()

const searchRuleProviders = ref('')
const pageRulProviders = ref(1)
const itemsPerPageRuleProviders = ref(10)

// Dialog State
const ruleProviderDialogVisible = ref(false)
const importRuleProvidersDialogVisible = ref(false)
const editingRuleProvider = ref<RuleProviderData | null>(null)
const editingRuleProviderName = ref<string | null>(null)
const loading = ref(false)

const filteredExtraRuleProviders = computed(() => {
  if (!searchRuleProviders.value) return props.ruleProviders
  const keyword = searchRuleProviders.value.toLowerCase()
  return props.ruleProviders.filter((item) =>
    Object.values(item).some((val) => String(val).toLowerCase().includes(keyword))
  )
})

const paginatedExtraRuleProviders = computed(() => {
  const start = (pageRulProviders.value - 1) * itemsPerPageRuleProviders.value
  const end = start + itemsPerPageRuleProviders.value
  return filteredExtraRuleProviders.value.slice(start, end)
})

const pageCountExtraRuleProviders = computed(() => {
  if (itemsPerPageRuleProviders.value === -1) {
    return 1
  }
  return Math.ceil(props.ruleProviders.length / itemsPerPageRuleProviders.value)
})

// Actions
function openAddRuleProviderDialog() {
  editingRuleProviderName.value = null
  editingRuleProvider.value = null
  ruleProviderDialogVisible.value = true
}

function openImportRuleProvidersDialog() {
  importRuleProvidersDialogVisible.value = true
}

function editRuleProvider(name: string) {
  const ruleProvider = props.ruleProviders.find((r) => r.name === name)
  if (ruleProvider) {
    editingRuleProviderName.value = name
    editingRuleProvider.value = structuredClone(toRaw(ruleProvider))
    ruleProviderDialogVisible.value = true
  }
}

async function deleteRuleProvider(name: string) {
  loading.value = true
  try {
    const n = encodeURIComponent(name)
    await props.api.delete(`/plugin/ClashRuleProvider/rule-providers/${n}`)
    emit('refresh', ['rule-providers'])
  } catch (err: unknown) {
    if (err instanceof Error) emit('show-error', err.message || '删除规则集合失败')
  } finally {
    loading.value = false
  }
}

async function handleStatusChange(name: string, disabled: boolean) {
  loading.value = true
  try {
    const provider = props.ruleProviders.find((p) => p.name === name)
    if (!provider) {
      emit('show-error', 'Rule provider not found')
      return
    }
    const n = encodeURIComponent(name)
    // Send full metadata with updated disabled status
    const newMeta = { ...provider.meta, disabled: disabled }
    await props.api.patch(`/plugin/ClashRuleProvider/rule-providers/${n}/meta`, newMeta)
    emit('refresh', ['rule-providers'])
  } catch (err: unknown) {
    if (err instanceof Error) {
      emit('show-error', err.message || '更新规则集合状态失败')
    }
  } finally {
    loading.value = false
  }
}

function editVisibility(name: string) {
  const provider = props.ruleProviders.find((p) => p.name === name)
  if (!provider) {
    emit('show-error', 'Rule provider not found')
    return
  }
  const n = encodeURIComponent(name)
  emit(
    'edit-visibility',
    provider.meta,
    `/plugin/ClashRuleProvider/rule-providers/${n}/meta`,
    'rule-providers'
  )
}

function closeRuleProviderDialog() {
  editingRuleProviderName.value = null
  ruleProviderDialogVisible.value = false
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
            v-model="searchRuleProviders"
            label="搜索规则集合"
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
            <v-btn icon="mdi-import" :disabled="loading" @click="openImportRuleProvidersDialog"> </v-btn>
            <v-btn icon="mdi-plus" :disabled="loading" @click="openAddRuleProviderDialog"> </v-btn>
          </v-btn-group>
        </v-col>
      </v-row>
    </div>
    <!-- 桌面端表格 -->
    <div class="d-none d-sm-flex clash-data-table">
      <RuleProvidersTable
        :items-per-page="itemsPerPageRuleProviders"
        :page="pageRulProviders"
        :rule-providers="filteredExtraRuleProviders"
        @edit-rule-provider="editRuleProvider"
        @delete-rule-provider="deleteRuleProvider"
        @show-yaml="(o) => emit('show-yaml', o)"
        @change-status="handleStatusChange"
        @edit-visibility="editVisibility"
      ></RuleProvidersTable>
    </div>
    <!-- 移动端卡片 -->
    <div class="d-sm-none">
      <v-row>
        <v-col v-for="item in paginatedExtraRuleProviders" :key="item.name" cols="12">
          <RuleProviderCard
            :rule-provider-data="item"
            @edit-rule-provider="editRuleProvider"
            @delete-rule-provider="deleteRuleProvider"
            @show-yaml="(o) => emit('show-yaml', o)"
            @change-status="handleStatusChange"
            @edit-visibility="editVisibility"
          ></RuleProviderCard>
        </v-col>
      </v-row>
    </div>
    <div class="pa-4" style="min-height: 4rem">
      <v-row align="center" no-gutters>
        <v-col cols="2" md="1"> </v-col>
        <v-col cols="8" md="10" class="d-flex justify-center">
          <!-- 桌面端分页器：只在 sm 及以上显示 -->
          <v-pagination
            v-model="pageRulProviders"
            :length="pageCountExtraRuleProviders"
            total-visible="5"
            rounded="circle"
            class="d-none d-sm-flex my-0"
            :disabled="loading"
          />
          <!-- 移动端分页器：只在 sm 以下显示 -->
          <v-pagination
            v-model="pageRulProviders"
            :length="pageCountExtraRuleProviders"
            total-visible="0"
            rounded="circle"
            class="d-sm-none my-0"
            :disabled="loading"
          />
        </v-col>
        <v-col cols="2" md="1" class="d-flex justify-end">
          <v-menu>
            <template #activator="{ props }">
              <v-btn v-bind="props" icon rounded="circle" variant="tonal" :disabled="loading">
                {{ pageTitle(itemsPerPageRuleProviders) }}
              </v-btn>
            </template>
            <v-list>
              <v-list-item
                v-for="(item, index) in itemsPerPageOptions"
                :key="index"
                :value="item.value"
                @click="itemsPerPageRuleProviders = item.value"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
      </v-row>
    </div>
    <v-divider></v-divider>

    <RuleProviderDialog
      v-if="ruleProviderDialogVisible"
      v-model="ruleProviderDialogVisible"
      :initial-value="editingRuleProvider"
      :is-adding="editingRuleProviderName === null"
      :api="api"
      @close="closeRuleProviderDialog"
      @refresh="emit('refresh', ['rule-providers'])"
      @show-snackbar="(val) => emit('show-snackbar', val)"
      @show-error="(msg) => emit('show-error', msg)"
    ></RuleProviderDialog>
    <ImportRuleProvidersDialog
      v-model="importRuleProvidersDialogVisible"
      :api="api"
      @refresh="emit('refresh', ['rule-providers'])"
      @show-snackbar="(val) => emit('show-snackbar', val)"
      @show-error="(msg) => emit('show-error', msg)"
    ></ImportRuleProvidersDialog>
  </div>
</template>

<style scoped></style>
