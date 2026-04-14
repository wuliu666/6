<template>
  <el-container class="dashboard-container">
    <el-aside width="240px" class="sidebar">
      <div class="logo">✨ 九雨创作台</div>
      <el-menu router :default-active="$route.path" class="el-menu-vertical" background-color="transparent" text-color="#fff" active-text-color="#ffd04b">
        <el-menu-item index="/dashboard/drawing"><el-icon><Picture /></el-icon><span>AI 绘图板</span></el-menu-item>
        <el-menu-item index="/dashboard/storyboard"><el-icon><VideoCamera /></el-icon><span>分镜生成器</span></el-menu-item>
        <el-menu-item index="/dashboard/assets"><el-icon><Files /></el-icon><span>团队素材库</span></el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">欢迎回来，{{ username }}</div>
        <div class="header-right">
          <el-button type="danger" plain size="small" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Picture, VideoCamera, Files } from '@element-plus/icons-vue'

const router = useRouter()
const username = ref('创作者')

// 页面加载时，从本地保险箱拿出用户名
onMounted(() => {
  const userStr = localStorage.getItem('jiuyu_user')
  if (userStr) {
    const user = JSON.parse(userStr)
    username.value = user.username
  }
})

// 退出登录逻辑：清空保险箱，踢回登录页
const handleLogout = () => {
  localStorage.removeItem('jiuyu_token')
  localStorage.removeItem('jiuyu_user')
  router.push('/login')
}
</script>

<style scoped>
.dashboard-container {
  height: 100vh;
  background-color: #f0f2f5;
}
.sidebar {
  background: #2b2f3a;
  color: white;
  box-shadow: 2px 0 6px rgba(0,21,41,.35);
  z-index: 10;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 20px;
  font-weight: bold;
  letter-spacing: 2px;
  border-bottom: 1px solid #1f2229;
}
.el-menu-vertical {
  border-right: none;
}
.header {
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
  z-index: 9;
}
.main-content {
  padding: 20px;
}
.welcome-card {
  margin-top: 20px;
  border-radius: 12px;
}
</style>