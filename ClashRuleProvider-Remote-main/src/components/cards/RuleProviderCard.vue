<script setup lang="ts">
import {PropType} from 'vue'
import {RuleProviderData} from '@/components/types'
import {getBehaviorColor, getSourceColor} from '@/components/utils'
import RuleProviderActionMenu from '@/components/menu/RuleProviderActionMenu.vue'

defineProps({
  ruleProviderData: {
    type: Object as PropType<RuleProviderData>,
    required: true
  }
})
const emit = defineEmits<{
  (e: 'editRuleProvider', name: string): void
  (e: 'deleteRuleProvider', name: string): void
  (e: 'showYaml', obj: any): void
  (e: 'changeStatus', name: string, disabled: boolean): void
  (e: 'editVisibility', name: string): void
}>()
</script>

<template>
  <v-card
      rounded="lg"
      elevation="2"
      class="rule-provider-card h-100 transition-swing"
      variant="tonal"
  >
    <div class="d-flex justify-space-between align-center px-4 pt-3">
      <span class="font-weight-bold text-truncate" :title="ruleProviderData.name">{{
          ruleProviderData.name
        }}</span>
      <div class="d-flex align-center">
        <v-tooltip
            v-if="
            ruleProviderData.meta.invisible_to && ruleProviderData.meta.invisible_to.length > 0
          "
            text="已配置可见性限制"
            location="top"
        >
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" color="warning" class="mr-2">
              mdi-eye-off-outline
            </v-icon>
          </template>
        </v-tooltip>
        <v-chip
            size="small"
            :color="getSourceColor(ruleProviderData.meta.source)"
            variant="outlined"
        >
          {{ ruleProviderData.meta.source }}
        </v-chip>
      </div>
    </div>

    <v-card-text class="pt-2 pb-4">
      <v-row no-gutters class="mb-2 align-center">
        <v-col cols="3" class="text-caption text-medium-emphasis">类型</v-col>
        <v-col cols="9">
          <span class="text-body-2 font-weight-medium">{{ ruleProviderData.data.type }}</span>
        </v-col>
      </v-row>
    </v-card-text>
    <v-divider></v-divider>
    <v-card-actions>
      <v-icon :color="ruleProviderData.meta.disabled ? 'grey' : 'success'">
        {{
          ruleProviderData.meta.disabled ? 'mdi-close-circle-outline' : 'mdi-check-circle-outline'
        }}
      </v-icon>
      <v-spacer></v-spacer>
      <RuleProviderActionMenu
          :rule-provider="ruleProviderData"
          @change-status="(disabled) => emit('changeStatus', ruleProviderData.name, disabled)"
          @edit="emit('editRuleProvider', ruleProviderData.name)"
          @show-yaml="emit('showYaml', ruleProviderData.data)"
          @delete="emit('deleteRuleProvider', ruleProviderData.name)"
          @edit-visibility="emit('editVisibility', ruleProviderData.name)"
      />
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.rule-provider-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}
</style>
