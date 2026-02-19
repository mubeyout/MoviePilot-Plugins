<script setup lang="ts">
import { ref, PropType } from 'vue'
import { RuleData, RuleSetType } from '@/components/types'
import { getActionColor, getRuleTypeColor, timestampToDate } from '@/components/utils'
import { itemsPerPageOptions } from '@/components/constants'
import RuleActionMenu from '@/components/menu/RuleActionMenu.vue'

const props = defineProps({
  sortedRules: {
    type: Array as PropType<RuleData[]>,
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
  searchRule: String
})

const emit = defineEmits<{
  (e: 'edit', priority: number, type: RuleSetType): void
  (e: 'delete', priority: number, type: RuleSetType): void
  (e: 'delete-batch', priorities: number[], type: RuleSetType): void
  (e: 'reorder', targetPriority: number, movedPriority: number, type: RuleSetType): void
  (e: 'change-status', priority: number, disabled: boolean, type: RuleSetType): void
  (e: 'change-status-batch', priorities: number[], disabled: boolean, type: RuleSetType): void
  (e: 'editVisibility', priority: number, type: RuleSetType): void
}>()

const headers = ref([
  { title: '', key: 'handler', sortable: false, width: '1rem' },
  { title: '优先级', key: 'priority', sortable: true, width: '3.5rem' },
  { title: '类型', key: 'type', sortable: true },
  { title: '内容', key: 'payload', sortable: true },
  { title: '出站', key: 'action', sortable: false },
  { title: '日期', key: 'time_modified', sortable: true },
  { title: '', key: 'status', sortable: false, width: '1rem' },
  { title: '', key: 'actions', sortable: false, width: '1rem' }
])

const dragEnabled = ref(false)
const hoveredPriority = ref<number>(-1)
const ruleset = 'top'
const dragItem = ref<RuleData | null>(null)
const selected = ref<number[]>([])

function dragStart(event: DragEvent, priority: number) {
  const item = props.sortedRules.find((r) => r.priority === priority)
  if (!item) {
    event.preventDefault?.()
    return
  }
  dragItem.value = item
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function dragOver(event: DragEvent, priority: number) {
  event.preventDefault()
  hoveredPriority.value = priority
}

function drop(event: DragEvent, targetPriority: number) {
  if (dragItem.value && dragItem.value.priority !== targetPriority) {
    emit('reorder', targetPriority, dragItem.value.priority, ruleset)
  }
  dragItem.value = null
  hoveredPriority.value = -1
}

function dragEnd() {
  dragItem.value = null
  hoveredPriority.value = -1
}

function editRule(priority: number) {
  emit('edit', priority, ruleset)
}

function deleteRule(priority: number) {
  emit('delete', priority, ruleset)
}

function deleteSelected() {
  if (selected.value.length > 0) {
    emit('delete-batch', selected.value, ruleset)
    selected.value = []
  }
}

function updateStatus(item: RuleData, disabled: boolean) {
  emit('change-status', item.priority, disabled, ruleset)
}

function changeBatchStatus(disabled: boolean) {
  if (selected.value.length > 0) {
    emit('change-status-batch', selected.value, disabled, ruleset)
    selected.value = []
  }
}

const rowProps = (data: any) => {
  const item = data.item as RuleData
  return {
    class: {
      'drop-over': item.priority === hoveredPriority.value,
      'dragging-item': dragItem.value?.priority === item.priority,
      'list-row': true,
      'text-grey': item.meta?.disabled
    },
    draggable: dragEnabled.value,
    onDragstart: (e: DragEvent) => dragStart(e, item.priority),
    onDragover: (e: DragEvent) => dragOver(e, item.priority),
    onDrop: (e: DragEvent) => drop(e, item.priority),
    onDragend: dragEnd
  }
}
</script>

<template>
  <v-data-table
    v-model="selected"
    class="px-4"
    :headers="headers"
    :search="searchRule"
    :items="sortedRules"
    :page="page"
    :items-per-page="itemsPerPage"
    :items-per-page-options="itemsPerPageOptions"
    item-key="priority"
    item-value="priority"
    show-select
    density="compact"
    hide-default-footer
    fixed-header
    :row-props="rowProps"
  >
    <template #top>
      <teleport v-if="selected.length > 0" to="#top-rules-table-batch-actions">
        <v-btn-group rounded variant="tonal">
          <v-btn
            color="success"
            prepend-icon="mdi-check"
            size="small"
            @click="changeBatchStatus(false)"
          >
          </v-btn>
          <v-btn
            color="warning"
            prepend-icon="mdi-close"
            size="small"
            @click="changeBatchStatus(true)"
          >
          </v-btn>
          <v-btn
            color="error"
            prepend-icon="mdi-trash-can-outline"
            size="small"
            @click="deleteSelected"
          >
          </v-btn>
        </v-btn-group>
      </teleport>
    </template>
    <template #item.handler="{}">
      <v-icon class="drag-handle" @mouseenter="dragEnabled = true" @mouseleave="dragEnabled = false"
        >mdi-drag-horizontal-variant
      </v-icon>
    </template>
    <template #item.priority="{ item }">
      <v-chip size="x-small" variant="tonal" color="secondary" class="font-weight-bold">
        {{ item.priority }}
      </v-chip>
    </template>

    <template #item.type="{ item }">
      <v-chip :color="getRuleTypeColor(item.type)" size="small" label variant="tonal">
        {{ item.type }}
      </v-chip>
    </template>
    <template #item.payload="{ value }">
      <small>{{ value }}</small>
    </template>
    <template #item.action="{ item }">
      <v-chip :color="getActionColor(item.action)" size="small" variant="outlined" pill>
        {{ item.action }}
      </v-chip>
    </template>

    <template #item.time_modified="{ item }">
      <small>{{ item.meta?.time_modified ? timestampToDate(item.meta.time_modified) : '' }}</small>
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
      <RuleActionMenu
        :rule="item"
        @edit="editRule(item.priority)"
        @delete="deleteRule(item.priority)"
        @change-status="(disabled) => updateStatus(item, disabled)"
        @edit-visibility="emit('editVisibility', item.priority, ruleset)"
      />
    </template>
  </v-data-table>
</template>
