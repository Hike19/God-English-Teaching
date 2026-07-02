<template>
  <header class="header-bar">
    <div class="logo">God English</div>
    <div class="actions">
      <ImportUpload @uploaded="onTaskCreated" />
      <PasteUrl @submitted="onTaskCreated" />
    </div>
  </header>
</template>

<script setup lang="ts">
import ImportUpload from './ImportUpload.vue'
import PasteUrl from './PasteUrl.vue'
import { useTasksStore } from '@/stores/tasks'

const tasksStore = useTasksStore()

async function onTaskCreated(taskId: number) {
  await tasksStore.fetchTask(taskId)
}
</script>

<style scoped>
.header-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1.5rem; background: #1a1a2e; border-bottom: 1px solid #333;
}
.logo {
  font-size: 1.25rem; font-weight: 700; color: #4fc3f7; letter-spacing: 1px;
}
.actions { display: flex; gap: 1rem; align-items: center; }
</style>
