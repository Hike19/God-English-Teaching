import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoginModal from '../LoginModal.vue'

describe('LoginModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders login form by default', () => {
    const wrapper = mount(LoginModal, { props: {} })
    expect(wrapper.find('h2').text()).toBe('登录')
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('toggles between login and register', async () => {
    const wrapper = mount(LoginModal, { props: {} })
    await wrapper.find('a').trigger('click')
    expect(wrapper.find('h2').text()).toBe('注册')
    await wrapper.find('a').trigger('click')
    expect(wrapper.find('h2').text()).toBe('登录')
  })

  it('emits close on overlay click', async () => {
    const wrapper = mount(LoginModal, { props: {} })
    await wrapper.find('.modal-overlay').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on X button click', async () => {
    const wrapper = mount(LoginModal, { props: {} })
    await wrapper.find('.close-btn').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
