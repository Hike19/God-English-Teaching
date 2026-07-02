import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const playbackRate = ref(1.0)
  const audioRef = ref<HTMLAudioElement | null>(null)

  const formattedCurrentTime = computed(() => formatTime(currentTime.value))
  const formattedDuration = computed(() => formatTime(duration.value))
  const progress = computed(() =>
    duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
  )

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  function setAudio(el: HTMLAudioElement | null) {
    audioRef.value = el
  }

  function togglePlay() {
    const a = audioRef.value
    if (!a) return
    if (a.paused) {
      a.play()
      isPlaying.value = true
    } else {
      a.pause()
      isPlaying.value = false
    }
  }

  function seek(time: number) {
    const a = audioRef.value
    if (!a) return
    a.currentTime = time
    currentTime.value = time
  }

  function seekByPercent(percent: number) {
    seek((percent / 100) * duration.value)
  }

  function setRate(rate: number) {
    const a = audioRef.value
    if (!a) return
    a.playbackRate = rate
    playbackRate.value = rate
  }

  function onTimeUpdate(time: number) {
    currentTime.value = time
  }

  function onLoadedMetadata(dur: number) {
    duration.value = dur
  }

  function onEnded() {
    isPlaying.value = false
  }

  function onPlay() {
    isPlaying.value = true
  }

  function onPause() {
    isPlaying.value = false
  }

  return {
    isPlaying, currentTime, duration, playbackRate,
    formattedCurrentTime, formattedDuration, progress,
    setAudio, togglePlay, seek, seekByPercent, setRate,
    onTimeUpdate, onLoadedMetadata, onEnded, onPlay, onPause,
  }
})
