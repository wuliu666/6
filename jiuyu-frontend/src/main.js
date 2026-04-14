import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 引入组件库的 CSS
import * as ElementPlusIconsVue from '@element-plus/icons-vue' // 引入图标库
import router from './router' // 引入我们刚写的路由
import './style.css' // 引入我们自己的全局样式

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router) // 启动路由魔法！
app.mount('#app')