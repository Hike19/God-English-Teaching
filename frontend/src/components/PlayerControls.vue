<template>
  <div class="player-controls">
    <button class="play-btn" @click="player.togglePlay()">
      {{ player.isPlaying ? '⏸' : '▶' }}
    </button>

    <span class="time">{{ player.formattedCurrentTime }}</span>

    <div
      class="progress-bar"
      ref="barRef"
      @click="clickBar"
      @mousedown="startDrag"
    >
      <div class="progress-fill" :style="{ width: player.progress + '%' }" />
    </div>

    <span class="time">{{ player.formattedDuration }}</span>

    <select
      class="rate-select"
      :value="player.playbackRate"
      @change="player.setRate(Number(($event.target as HTMLSelectElement).value))"
    >
      <option v-for="r in rates" :key="r" :value="r">{{ r }}x</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePlayerStore } from '@/stores/player'

const player = usePlayerStore()
const rates = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
const barRef = ref<HTMLDivElement>()
let dragging = false

function clickBar(e: MouseEvent) {
  const bar = barRef.value
  if (!bar) return
  const rect = bar.getBoundingClientRect()
  const percent = ((e.clientX - rect.left) / rect.width) * 100
  player.seekByPercent(percent)
}

function startDrag(e: MouseEvent) {
  dragging = true
  const bar = barRef.value
  if (!bar) return

  function onMove(ev: MouseEvent) {
    if (!dragging || !bar) return
    const rect = bar.getBoundingClientRect()
    const percent = Math.max(0, Math.min(100, ((ev.clientX - rect.left) / rect.width) * 100))
    player.seekByPercent(percent)
  }

  function onUp() {
    dragging = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)

  onMove(e)
}
</script>

<style scoped>
.player-controls {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 1rem; background: #1a1a2e; border-radius: 8px;
}
.play-btn {
  background: none; border: none; color: #e0e0e0; font-size: 1.5rem; cursor: pointer;
}
.time { font-size: 0.8rem; color: #999; min-width: 3rem; text-align: center; }
.progress-bar {
  flex: 1; height: 6px; background: #333; border-radius: 3px; cursor: pointer; position: relative;
}
.progress-fill {
  height: 100%; background: #4fc3f7; border-radius: 3px; transition: width 0.1s linear;
}
.rate-select {
  background: #16213e; color: #e0e0e0; border: 1px solid #333;
  border-radius: 4px; padding: 0.25rem; font-size: 0.8rem;
}
</style>
