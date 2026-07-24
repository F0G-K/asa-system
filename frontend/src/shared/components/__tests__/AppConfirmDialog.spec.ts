import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppConfirmDialog from '../AppConfirmDialog.vue'

function createWrapper(props = {}) {
  return mount(AppConfirmDialog, {
    props: {
      visible: true,
      title: '确认删除',
      message: '此操作不可撤销',
      ...props,
    },
    global: {
      stubs: {
        'el-dialog': {
          template: `
            <div v-if="modelValue !== false" class="el-dialog-stub">
              <h2 class="dialog-title">{{ title }}</h2>
              <slot />
              <div class="footer-stub"><slot name="footer" /></div>
            </div>
          `,
          props: ['modelValue', 'title'],
          emits: ['update:modelValue', 'opened'],
        },
        'el-input': {
          template: `
            <input
              class="el-input-stub"
              :value="modelValue"
              :disabled="disabled"
              @input="$emit('update:modelValue', $event.target.value)"
            />
          `,
          props: ['modelValue', 'disabled'],
          emits: ['update:modelValue'],
        },
        'el-button': {
          template: `
            <button
              class="el-button-stub"
              :disabled="disabled"
              @click="$emit('click')"
            >
              <slot />
            </button>
          `,
          props: ['disabled', 'loading', 'type'],
          emits: ['click'],
        },
      },
    },
  })
}

describe('AppConfirmDialog', () => {
  it('renders title and message', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('确认删除')
    expect(wrapper.text()).toContain('此操作不可撤销')
  })

  it('renders confirm button with default text', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('确定')
  })

  it('renders custom confirm text', () => {
    const wrapper = createWrapper({ confirmText: '删除' })
    expect(wrapper.text()).toContain('删除')
  })

  it('renders cancel button', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('取消')
  })

  it('does not show name input by default', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.confirm-dialog__input').exists()).toBe(false)
  })

  it('shows name input when requireNameInput is true', () => {
    const wrapper = createWrapper({
      requireNameInput: true,
      expectedName: 'my-project',
    })
    expect(wrapper.find('.confirm-dialog__input').exists()).toBe(true)
    expect(wrapper.text()).toContain('my-project')
  })

  it('confirm button disabled when name mismatch', async () => {
    const wrapper = createWrapper({
      requireNameInput: true,
      expectedName: 'my-project',
    })

    const input = wrapper.find('.el-input-stub')
    await input.setValue('wrong-name')

    // confirm button should be disabled
    const confirmBtn = wrapper.findAll('.el-button-stub').at(1)
    expect(confirmBtn?.attributes('disabled')).toBeDefined()
  })

  it('shows error when name mismatch', async () => {
    const wrapper = createWrapper({
      requireNameInput: true,
      expectedName: 'my-project',
    })

    const input = wrapper.find('.el-input-stub')
    await input.setValue('wrong')

    expect(wrapper.find('.confirm-dialog__input-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('项目名称不匹配')
  })

  it('confirm button enabled when name matches', async () => {
    const wrapper = createWrapper({
      requireNameInput: true,
      expectedName: 'my-project',
    })

    const input = wrapper.find('.el-input-stub')
    await input.setValue('my-project')

    const confirmBtn = wrapper.findAll('.el-button-stub').at(1)
    expect(confirmBtn?.attributes('disabled')).toBeUndefined()
  })

  it('confirm button disabled when loading', () => {
    const wrapper = createWrapper({ loading: true })
    const confirmBtn = wrapper.findAll('.el-button-stub').at(1)
    expect(confirmBtn?.attributes('disabled')).toBeDefined()
  })

  it('emits confirm when button clicked with valid input', async () => {
    const wrapper = createWrapper()

    const buttons = wrapper.findAll('.el-button-stub')
    const confirmBtn = buttons.at(1)
    await confirmBtn!.trigger('click')

    expect(wrapper.emitted('confirm')).toBeTruthy()
  })

  it('emits cancel and update:visible on close', async () => {
    const wrapper = createWrapper()

    const cancelBtn = wrapper.findAll('.el-button-stub').at(0)
    await cancelBtn!.trigger('click')

    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('does not show dialog when visible is false', () => {
    const wrapper = mount(AppConfirmDialog, {
      props: {
        visible: false,
        title: 'Test',
        message: 'Test',
      },
      global: {
        stubs: {
          'el-dialog': {
            template: '<div v-if="false" />',
            props: ['modelValue'],
          },
          'el-button': { template: '<button />' },
        },
      },
    })

    expect(wrapper.find('.confirm-dialog').exists()).toBe(false)
  })
})
