import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import App from '@/app/App.vue'
import { router } from '@/router'
import { bootstrap } from '@/app/bootstrap'

import '@/shared/styles/variables.css'
import '@/shared/styles/reset.css'
import '@/shared/styles/global.css'

async function init() {
  const app = createApp(App)

  const pinia = createPinia()
  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)

  // 先 bootstrap（含 dev mode 激活），再挂载应用，避免组件在 dev mode 生效前发起 API 请求
  await bootstrap()

  app.mount('#app')
}

init().catch((err) => {
  console.error('Application failed to initialize:', err)
  document.body.innerHTML =
    '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#e34f4f;">系统初始化失败，请刷新页面重试</div>'
})
