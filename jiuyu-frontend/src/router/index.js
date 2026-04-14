import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginView },
    { 
      path: '/dashboard', 
      component: DashboardView,
      redirect: '/dashboard/storyboard', // 默认一进来就显示分镜生成器
      children: [
        { 
          path: 'storyboard', 
          component: () => import('../views/StoryboardView.vue') 
        },
        // 以后还可以接着加 drawing 和 assets 页面
        // 👈 新增下面这三行，逗号别漏了！
        {
          path: 'assets',
          component: () => import('../views/AssetsView.vue')
        },
        // 👈 新增下面这四行（把它放在 storyboard 前面或后面都可以）
        {
          path: 'drawing',
          component: () => import('../views/DrawingView.vue')
        },
        { 
          path: 'storyboard', 
          component: () => import('../views/StoryboardView.vue') 
        },
        {
          path: 'assets',
          component: () => import('../views/AssetsView.vue')
        }

    
      ]
    }
  ]
})

// 🛡️ 路由守卫：没带通行证的人，统统拦在门外！
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('jiuyu_token')
  if (to.path === '/dashboard' && !token) {
    next('/login') // 没 token 想进工作台？踢回登录页！
  } else {
    next() // 放行
  }
})

export default router