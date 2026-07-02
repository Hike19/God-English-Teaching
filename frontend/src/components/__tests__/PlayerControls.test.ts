import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PlayerControls from '../PlayerControls.vue'

describe('PlayerControls', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders play button', () => {
    const wrapper = mount(PlayerControls)
    expect(wrapper.find('.play-btn').exists()).toBe(true)
    expect(wrapper.find('.play-btn').text()).toBe('▶')
  })

  it('renders speed select with all options', () => {
    const wrapper = mount(PlayerControls)
    const options = wrapper.findAll('.rate-select option')
    expect(options).toHaveLength(6)
    expect(options[0].text()).toBe('0.5x')
    expect(options[5].text()).toBe('2x')
  })

  it('shows time displays', () => {
    const wrapper = mount(PlayerControls)
    const times = wrapper.findAll('.time')
    expect(times).toHaveLength(2)
  })

  it('renders progress bar', () => {
    const wrapper = mount(PlayerControls)
    expect(wrapper.find('.progress-bar').exists()).toBe(true)
    expect(wrapper.find('.progress-fill').exists()).toBe(true)
  })
})
