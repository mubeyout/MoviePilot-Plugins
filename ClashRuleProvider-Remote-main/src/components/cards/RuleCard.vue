<script setup lang="ts">
import { PropType } from 'vue'
import { RuleData, RuleSetType } from '@/components/types'
import { getActionColor, getRuleTypeColor } from '@/components/utils'
import RuleActionMenu from '@/components/menu/RuleActionMenu.vue'

const props = defineProps({
  rule: {
    type: Object as PropType<RuleData>,
    required: true
  },
  ruleset: {
    type: Object as PropType<RuleSetType>,
    required: true
  }
})

const emit = defineEmits<{
  (e: 'edit', priority: number, type: RuleSetType): void
  (e: 'delete', priority: number, type: RuleSetType): void
  (e: 'change-status', priority: number, disabled: boolean, type: RuleSetType): void
  (e: 'edit-visibility', priority: number, type: RuleSetType): void
}>()

function editRule(priority: number) {
  emit('edit', priority, props.ruleset)
}

function deleteRule(priority: number) {
  emit('delete', priority, props.ruleset)
}

function updateStatus(disabled: boolean) {
  emit('change-status', props.rule.priority, disabled, props.ruleset)
}

function editVisibility() {
  emit('edit-visibility', props.rule.priority, props.ruleset)
}
</script>

<template>
  <v-card rounded="lg" elevation="2" class="rule-card h-100 transition-swing" variant="tonal">
    <div class="d-flex justify-space-between align-center px-4 pt-3">
      <v-chip variant="flat" color="secondary" class="font-weight-bold mr-2" size="small">
        {{ rule.priority }}
      </v-chip>
      <v-tooltip
        v-if="rule.meta.invisible_to && rule.meta.invisible_to.length > 0"
        text="已配置可见性限制"
        location="top"
      >
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small" color="warning"> mdi-eye-off-outline </v-icon>
        </template>
      </v-tooltip>
    </div>

    <v-card-text class="pt-2 pb-4">
      <v-row no-gutters class="mb-2 align-center">
        <v-col cols="3" class="text-caption text-medium-emphasis">类型</v-col>
        <v-col cols="9">
          <v-chip
            :color="getRuleTypeColor(rule.type)"
            size="x-small"
            label
            variant="tonal"
            class="font-weight-medium"
          >
            {{ rule.type }}
          </v-chip>
        </v-col>
      </v-row>

      <v-row no-gutters class="mb-2 align-center">
        <v-col cols="3" class="text-caption text-medium-emphasis">内容</v-col>
        <v-col cols="9" class="text-body-2 text-truncate font-weight-bold">
          <span :title="rule.payload">{{ rule.payload }}</span>
        </v-col>
      </v-row>

      <v-row no-gutters class="align-center">
        <v-col cols="3" class="text-caption text-medium-emphasis">出站</v-col>
        <v-col cols="9">
          <v-chip
            :color="getActionColor(rule.action)"
            size="x-small"
            variant="outlined"
            class="font-weight-medium"
          >
            {{ rule.action }}
          </v-chip>
        </v-col>
      </v-row>
    </v-card-text>
    <v-divider></v-divider>
    <v-card-actions>
      <v-icon :color="rule.meta.disabled ? 'grey' : 'success'">
        {{ rule.meta.disabled ? 'mdi-close-circle-outline' : 'mdi-check-circle-outline' }}
      </v-icon>
      <v-spacer></v-spacer>
      <RuleActionMenu
        :rule="rule"
        :hide-visibility="ruleset == 'ruleset'"
        @edit="editRule(rule.priority)"
        @delete="deleteRule(rule.priority)"
        @change-status="updateStatus"
        @edit-visibility="editVisibility"
      />
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.rule-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}
</style>
