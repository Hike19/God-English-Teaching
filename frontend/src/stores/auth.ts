import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import type { User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function loginAction(username: string, password: string) {
    const result = await authApi.login(username, password)
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem('token', result.access_token)
  }

  async function registerAction(username: string, password: string) {
    const result = await authApi.register(username, password)
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem('token', result.access_token)
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      user.value = await authApi.getMe()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, loginAction, registerAction, fetchMe, logout }
})
