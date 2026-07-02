<template>
  <div class="history-page">
    <header class="history-header">
      <button @click="$router.push('/')">← 返回</button>
      <h1>历史任务</h1>
    </header>

    <div v-if="!auth.isLoggedIn" class="login-prompt">
      请先登录以查看历史记录
    </div>

    <div v-else-if="tasksStore.loading" class="loading">加载中...</div>

    <div v-else-if="!tasksStore.tasks.length" class="empty">
      暂无历史任务
    </div>

    <ul v-else class="task-list">
      <li v-for="task in tasksStore.tasks" :key="task.id" class="task-item">
        <div class="task-info">
          <span class="task-title">{{ task.title }}</span>
          <span class="task-status" :class="task.status">
            {{ statusLabel(task.status) }}
          </span>
          <span class="task-date">{{ formatDate(task.created_at) }}</span>
        </div>
        <div class="task-actions">
          <button v-if="task.status === 'done'" @click="playTask(task.id)">▶ 播放</button>
          <button @click="deleteTask(task.id)">删除</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTasksStore } from '@/stores/tasks'

const router = useRouter()
const auth = useAuthStore()
const tasksStore = useTasksStore()

onMounted(() => {
  if (auth.isLoggedIn) {
    tasksStore.fetchTasks()
  }
})

function statusLabel(status: string): string {
  return { processing: '处理中', done: '完成', failed: '失败' }[status] ?? status
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function playTask(taskId: number) {
  await tasksStore.fetchTask(taskId)
  router.push('/')
}

async function deleteTask(taskId: number) {
  if (!confirm('确定删除此任务？')) return
  await tasksStore.removeTask(taskId)
}
</script>

<style scoped>
.history-page {
  max-width: 800px; margin: 0 auto; padding: 1.5rem;
}
.history-header {
  display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;
}
.history-header button {
  padding: 0.4rem 0.75rem; border: none; border-radius: 6px;
  background: #333; color: #e0e0e0; cursor: pointer;
}
h1 { color: #e0e0e0; font-size: 1.5rem; }
.login-prompt, .loading, .empty { text-align: center; color: #666; padding: 3rem 1rem; }
.task-list { list-style: none; display: flex; flex-direction: column; gap: 0.75rem; }
.task-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1rem; background: #1a1a2e; border-radius: 8px;
}
.task-info { display: flex; flex-direction: column; gap: 0.25rem; }
.task-title { color: #e0e0e0; font-weight: 500; word-break: break-all; }
.task-status { font-size: 0.8rem; }
.task-status.done { color: #66bb6a; }
.task-status.processing { color: #ffa726; }
.task-status.failed { color: #ef5350; }
.task-date { font-size: 0.75rem; color: #666; }
.task-actions { display: flex; gap: 0.5rem; }
.task-actions button {
  padding: 0.4rem 0.75rem; border: none; border-radius: 6px;
  font-size: 0.85rem; cursor: pointer;
}
.task-actions button:first-child { background: #4fc3f7; color: #000; }
.task-actions button:last-child { background: #333; color: #ef5350; }
</style>
