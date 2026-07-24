import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppStatusTag from '../AppStatusTag.vue'

describe('AppStatusTag', () => {
  it('renders text from map for known value', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'running',
        map: {
          running: { text: '运行中', color: 'var(--color-primary)' },
        },
      },
    })

    expect(wrapper.text()).toContain('运行中')
  })

  it('renders "未知状态" fallback for unknown value', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'nonexistent',
        map: {},
      },
    })

    expect(wrapper.text()).toContain('未知状态')
  })

  it('renders aria-label from map', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'created',
        map: {
          created: {
            text: '已创建',
            color: 'var(--color-info)',
            ariaLabel: '项目状态：已创建',
          },
        },
      },
    })

    expect(wrapper.attributes('aria-label')).toBe('项目状态：已创建')
  })

  it('renders aria-label with text fallback when no ariaLabel', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'running',
        map: {
          running: { text: '运行中', color: 'var(--color-primary)' },
        },
      },
    })

    expect(wrapper.attributes('aria-label')).toBe('运行中')
  })

  it('applies size class', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'created',
        map: { created: { text: '已创建', color: '#666' } },
        size: 'small',
      },
    })

    expect(wrapper.classes()).toContain('status-tag--small')
  })

  it('applies default size by default', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'created',
        map: { created: { text: '已创建', color: '#666' } },
      },
    })

    expect(wrapper.classes()).toContain('status-tag--default')
  })

  it('renders dot and text elements', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'completed',
        map: { completed: { text: '已完成', color: 'var(--color-success)' } },
      },
    })

    expect(wrapper.find('.status-tag__dot').exists()).toBe(true)
    expect(wrapper.find('.status-tag__text').exists()).toBe(true)
  })

  it('sets CSS variable for color', () => {
    const wrapper = mount(AppStatusTag, {
      props: {
        value: 'failed',
        map: { failed: { text: '失败', color: 'var(--color-danger)' } },
      },
    })

    const el = wrapper.find('.status-tag')
    expect(el.attributes('style')).toContain('--tag-color')
  })

  it('renders all project statuses correctly', () => {
    const map = {
      created: { text: '已创建', color: 'var(--color-info)' },
      running: { text: '运行中', color: 'var(--color-primary)' },
      completed: { text: '已完成', color: 'var(--color-success)' },
      failed: { text: '失败', color: 'var(--color-danger)' },
      stopped: { text: '已停止', color: 'var(--color-warning)' },
    }

    for (const [status, display] of Object.entries(map)) {
      const wrapper = mount(AppStatusTag, {
        props: { value: status, map },
      })
      expect(wrapper.text()).toContain(display.text)
    }
  })

  it('renders all risk levels correctly', () => {
    const map = {
      critical: { text: '严重', color: 'var(--color-danger)' },
      high: { text: '高', color: 'var(--color-danger)' },
      medium: { text: '中', color: 'var(--color-warning)' },
      low: { text: '低', color: 'var(--color-info)' },
      info: { text: '信息', color: 'var(--color-text-secondary)' },
    }

    for (const [status, display] of Object.entries(map)) {
      const wrapper = mount(AppStatusTag, {
        props: { value: status, map },
      })
      expect(wrapper.text()).toContain(display.text)
    }
  })
})
