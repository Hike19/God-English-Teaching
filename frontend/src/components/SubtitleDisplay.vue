<template>
  <div class="subtitle-display" ref="containerRef">
    <div v-if="!subtitles.length" class="placeholder">
      上传文件或粘贴链接以生成字幕
    </div>
    <div
      v-for="sub in subtitles"
      :key="sub.id"
      :ref="(el) => setSubRef(sub.id, el as HTMLElement)"
      class="subtitle-line"
      :class="{ active: isActive(sub), played: isPlayed(sub), upcoming: isUpcoming(sub) }"
      @click="seekTo(sub.start_time)"
    >
      {{ sub.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePlayerStore } from '@/stores/player'
import type { Subtitle } from '@/api/tasks'

const props = defineProps<{ subtitles: Subtitle[] }>()
const player = usePlayerStore()
const containerRef = ref<HTMLElement>()
const subRefs = new Map<number, HTMLElement>()

function setSubRef(id: number, el: HTMLElement | null) {
  if (el) subRefs.set(id, el)
}

function isActive(sub: Subtitle): boolean {
  return player.currentTime >= sub.start_time && player.currentTime < sub.end_time
}

function isPlayed(sub: Subtitle): boolean {
  return player.currentTime >= sub.end_time
}

function isUpcoming(sub: Subtitle): boolean {
  return player.currentTime < sub.start_time
}

function seekTo(time: number) {
  player.seek(time)
}

watch(() => player.currentTime, () => {
  for (const sub of props.subtitles) {
    if (isActive(sub)) {
      const el = subRefs.get(sub.id)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
      break
    }
  }
})
</script>

<style scoped>
.subtitle-display {
  flex: 1; overflow-y: auto; padding: 1rem;
  max-height: 60vh;
}
.placeholder { text-align: center; color: #666; padding: 3rem 1rem; }
.subtitle-line {
  padding: 0.5rem 1rem; margin: 0.25rem 0; border-radius: 6px;
  font-size: 1.1rem; line-height: 1.6; cursor: pointer;
  transition: opacity 0.3s, background 0.3s;
  white-space: pre-line;
}
.subtitle-line.played { opacity: 0.3; color: #666; }
.subtitle-line.upcoming { opacity: 0.5; color: #999; }
.subtitle-line.active {
  opacity: 1; color: #fff; background: rgba(79, 195, 247, 0.15);
  font-weight: 600; font-size: 1.3rem;
}
</style>
