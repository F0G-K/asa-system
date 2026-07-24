import { describe, it, expect } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import AppEmptyState from '../AppEmptyState.vue'

function createWrapper(props = {}) {
  return mount(AppEmptyState, {
    props,
    global: {
      stubs: {
        'el-icon': {
          template: '<i class="el-icon-stub"><slot /></i>',
        },
        'el-button': {
          template: '<button class="el-button-stub" @click="$emit(\'click\')"><slot /></button>',
          emits: ['click'],
        },
        FolderOpened: {
          template: '<svg class="folder-opened-stub" />',
        },
      },
    },
  }) as VueWrapper<InstanceType<typeof AppEmptyState>>
}

describe('AppEmptyState', () => {
  it('renders default title', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('暂无数据')
  })

  it('renders custom title', () => {
    const wrapper = createWrapper({ title: '没有项目' })
    expect(wrapper.text()).toContain('没有项目')
  })

  it('does not render description when empty', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.empty-state__description').exists()).toBe(false)
  })

  it('renders description when provided', () => {
    const wrapper = createWrapper({ description: '请先创建一个项目' })
    expect(wrapper.find('.empty-state__description').exists()).toBe(true)
    expect(wrapper.text()).toContain('请先创建一个项目')
  })

  it('does not render action button when actionText is empty', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.empty-state__action').exists()).toBe(false)
  })

  it('renders action button when actionText provided', () => {
    const wrapper = createWrapper({ actionText: '创建项目' })
    const btn = wrapper.find('.empty-state__action')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('创建项目')
  })

  it('emits action event when button clicked', async () => {
    const wrapper = createWrapper({ actionText: '创建' })
    await wrapper.find('.empty-state__action').trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
    expect(wrapper.emitted('action')).toHaveLength(1)
  })

  it('renders icon element', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.el-icon-stub').exists()).toBe(true)
  })

  it('renders all three sections when full props provided', () => {
    const wrapper = createWrapper({
      title: '没有漏洞',
      description: '项目尚未发现安全漏洞',
      actionText: '刷新',
    })

    expect(wrapper.text()).toContain('没有漏洞')
    expect(wrapper.text()).toContain('项目尚未发现安全漏洞')
    expect(wrapper.text()).toContain('刷新')
  })
})
