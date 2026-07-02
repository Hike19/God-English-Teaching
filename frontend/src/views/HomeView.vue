<template>
  <div class="home">
    <HeaderBar />
    <main class="player-area">
      <PlayerPanel />
    </main>
    <FooterBar @login="showLogin = true" @feedback="showFeedback = true" />

    <LoginModal v-if="showLogin" @close="showLogin = false" />
    <FeedbackModal v-if="showFeedback" @close="showFeedback = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HeaderBar from '@/components/HeaderBar.vue'
import FooterBar from '@/components/FooterBar.vue'
import PlayerPanel from '@/components/PlayerPanel.vue'
import LoginModal from '@/components/LoginModal.vue'
import FeedbackModal from '@/components/FeedbackModal.vue'

const showLogin = ref(false)
const showFeedback = ref(false)
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.player-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
