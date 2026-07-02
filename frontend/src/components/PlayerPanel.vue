<template>
  <div class="player-panel">
    <div v-if="!tasksStore.currentTask" class="empty-state">
      导入素材或粘贴链接开始练习
    </div>
    <template v-else-if="tasksStore.currentTask.status === 'processing'">
      <div class="processing">
        <div class="spinner" />
        <p>正在处理音频并生成字幕...</p>
      </div>
    </template>
    <template v-else-if="tasksStore.currentTask.status === 'failed'">
      <div class="failed">
        <p>处理失败：{{ tasksStore.currentTask.error_msg }}</p>
      </div>
    </template>
    <template v-else>
      <audio
        ref="audioEl"
        :src="audioSrc"
        preload="auto"
        @timeupdate="player.onTimeUpdate(($event.target as HTMLAudioElement).currentTime)"
        @loadedmetadata="player.onLoadedMetadata(($event.target as HTMLAudioElement).duration)"
        @ended="player.onEnded()"
        @play="player.onPlay()"
        @pause="player.onPause()"
      />
      <SubtitleDisplay :subtitles="tasksStore.currentTask.subtitles" />
      <PlayerControls />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { usePlayerStore } from '@/stores/player'
import { getAudioUrl } from '@/api/tasks'
import SubtitleDisplay from './SubtitleDisplay.vue'
import PlayerControls from './PlayerControls.vue'

const tasksStore = useTasksStore()
const player = usePlayerStore()
const audioEl = ref<HTMLAudioElement>()

const audioSrc = computed(() =>
  tasksStore.currentTask ? getAudioUrl(tasksStore.currentTask.id) : ''
)

watch(audioEl, (el) => {
  player.setAudio(el ?? null)
}, { immediate: true })
</script>

<style scoped>
.player-panel {
  flex: 1; display: flex; flex-direction: column;
  justify-content: space-between;
}
.empty-state, .processing, .failed {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: #666; font-size: 1.1rem;
}
.processing { flex-direction: column; gap: 1rem; }
.spinner {
  width: 2rem; height: 2rem; border: 3px solid #333;
  border-top-color: #4fc3f7; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.failed { color: #ef5350; }
</style>
