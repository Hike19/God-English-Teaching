import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as tasksApi from '@/api/tasks'
import type { Task } from '@/api/tasks'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)

  async function fetchTasks() {
    loading.value = true
    try {
      tasks.value = await tasksApi.listTasks()
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id: number) {
    loading.value = true
    try {
      currentTask.value = await tasksApi.getTask(id)
    } finally {
      loading.value = false
    }
  }

  async function createFromFile(file: File, onProgress?: (pct: number) => void): Promise<number> {
    const result = await tasksApi.uploadFile(file, onProgress)
    await pollUntilDone(result.id)
    return result.id
  }

  async function createFromUrl(url: string): Promise<number> {
    const result = await tasksApi.submitUrl(url)
    await pollUntilDone(result.id)
    return result.id
  }

  async function pollUntilDone(taskId: number, intervalMs = 2000, timeoutMs = 600000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      const task = await tasksApi.getTask(taskId)
      if (task.status === 'done' || task.status === 'failed') {
        currentTask.value = task
        return
      }
      await new Promise((r) => setTimeout(r, intervalMs))
    }
    throw new Error('Task processing timed out')
  }

  async function removeTask(id: number) {
    await tasksApi.deleteTask(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
    if (currentTask.value?.id === id) {
      currentTask.value = null
    }
  }

  return { tasks, currentTask, loading, fetchTasks, fetchTask, createFromFile, createFromUrl, removeTask }
})
