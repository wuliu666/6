<template>
  <div class="auth-container">
    <el-card class="glass-card" shadow="hover">
      <div class="logo-area">
        <h2>✨ 九雨创作台</h2>
        <p class="subtitle">{{ isLogin ? '欢迎回来，创作者' : '使用专属邀请码加入我们' }}</p>
      </div>

      <el-form v-if="isLogin" :model="loginForm" class="auth-form" @submit.prevent>
        <el-form-item>
          <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" clearable />
        </el-form-item>
        <el-form-item>
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" class="submit-btn" size="large" round @click="handleLogin">登 录</el-button>
      </el-form>

      <el-form v-else :model="registerForm" class="auth-form" @submit.prevent>
        <el-form-item>
          <el-input v-model="registerForm.username" placeholder="你想使用的用户名" size="large" clearable />
        </el-form-item>
        <el-form-item>
          <el-input v-model="registerForm.password" type="password" placeholder="设置你的密码" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-input v-model="registerForm.inviteCode" placeholder="输入管理员发放的邀请码 (JIUYU-...)" size="large" clearable />
        </el-form-item>
        <el-button type="success" class="submit-btn" size="large" round @click="handleRegister">立 即 注 册</el-button>
      </el-form>

      <div class="switch-mode">
        <el-button link @click="isLogin = !isLogin">
          {{ isLogin ? '没有账号？使用邀请码注册' : '已有账号？返回登录' }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router' // 👈 新增这行

const router = useRouter() // 👈 新增这行

const isLogin = ref(true)

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', password: '', inviteCode: '' })

// 🔌 配置后端的基准地址
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000'
})

// 🚀 处理注册逻辑
const handleRegister = async () => {
  if (!registerForm.value.username || !registerForm.value.password || !registerForm.value.inviteCode) {
    ElMessage.warning('请把信息填写完整哦！')
    return
  }

  try {
    // 向我们之前写好的 FastAPI 注册接口发请求
    const response = await api.post('/auth/register', {
      username: registerForm.value.username,
      password: registerForm.value.password,
      invite_code: registerForm.value.inviteCode // 注意这里要和后端的字段名对齐
    })
    
    // 如果成功，弹出绿色的成功提示
    ElMessage.success(response.data.message)
    // 自动切回登录界面
    isLogin.value = true
    
  } catch (error) {
    // 如果失败（比如邀请码错误、用户名重复），弹出红色的报错提示
    const errorMsg = error.response?.data?.detail || '注册失败，请检查网络'
    ElMessage.error(errorMsg)
  }
}

// 🔐 处理真实的登录逻辑
const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入完整的用户名和密码！')
    return
  }

  try {
    // 1. 拿着账号密码去敲后端的门
    const response = await api.post('/auth/login', {
      username: loginForm.value.username,
      password: loginForm.value.password
    })
    
    // 2. 登录成功，弹出绿色欢迎语
    ElMessage.success(response.data.message)
    
    // 3. 🌟 最关键的一步：把后端发的通行证和用户信息，死死地存在浏览器里！
    localStorage.setItem('jiuyu_token', response.data.access_token)
    localStorage.setItem('jiuyu_user', JSON.stringify(response.data.user))

    // 4. 打印出来看看（你可以按 F12 在控制台里看到）
    console.log("拿到的通行证：", response.data.access_token)
    
    // 稍后我们将在这里写：跳转到后台主界面的代码
    router.push('/dashboard')
    
  } catch (error) {
    // 如果密码错了，弹出红色的报错提示
    const errorMsg = error.response?.data?.detail || '登录失败，请检查网络或账号'
    ElMessage.error(errorMsg)
  }
}
</script>

<style scoped>
/* 整个页面的全屏背景 */
.auth-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  /* 我们可以用一个轻量级的动态渐变背景，或者先用极简的纯色 */
  background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
}

/* 核心：毛玻璃卡片特效 */
.glass-card {
  width: 400px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.65) !important; /* 半透明白色 */
  backdrop-filter: blur(12px); /* 背景虚化，也就是毛玻璃核心 */
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  padding: 20px;
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
}

.logo-area {
  text-align: center;
  margin-bottom: 30px;
}

.logo-area h2 {
  margin: 0;
  font-size: 26px;
  color: #303133;
}

.subtitle {
  color: #606266;
  font-size: 14px;
  margin-top: 8px;
}

.auth-form {
  margin-top: 20px;
}

.submit-btn {
  width: 100%;
  margin-top: 10px;
  font-weight: bold;
}

.switch-mode {
  text-align: center;
  margin-top: 20px;
}
</style>