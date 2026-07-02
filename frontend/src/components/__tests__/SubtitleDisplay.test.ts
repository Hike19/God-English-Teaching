import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SubtitleDisplay from '../SubtitleDisplay.vue'

const sampleSubtitles = [
  { id: 1, index: 0, start_time: 0, end_time: 2, text: 'Hello world' },
  { id: 2, index: 1, start_time: 2, end_time: 4, text: 'How are you?' },
  { id: 3, index: 2, start_time: 4, end_time: 6, text: 'I am fine.' },
]

describe('SubtitleDisplay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows placeholder when no subtitles', () => {
    const wrapper = mount(SubtitleDisplay, { props: { subtitles: [] } })
    expect(wrapper.find('.placeholder').exists()).toBe(true)
  })

  it('renders all subtitle lines', () => {
    const wrapper = mount(SubtitleDisplay, { props: { subtitles: sampleSubtitles } })
    const lines = wrapper.findAll('.subtitle-line')
    expect(lines).toHaveLength(3)
    expect(lines[0].text()).toBe('Hello world')
    expect(lines[1].text()).toBe('How are you?')
    expect(lines[2].text()).toBe('I am fine.')
  })
})
