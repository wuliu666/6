<template>
  <div class="assets-container">
    <div class="toolbar">
      <el-radio-group v-model="currentView" size="large" class="mode-switch">
        <el-radio-button label="team">🌐 团队公共素材库</el-radio-button>
        <el-radio-button label="personal">🔒 我的私密素材</el-radio-button>
      </el-radio-group>

      <el-upload
        class="upload-btn"
        action="http://127.0.0.1:8000/assets/upload"
        :show-file-list="false"
        :data="uploadData"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
      >
        <el-button type="primary" size="large" round>
          <el-icon class="el-icon--left"><Upload /></el-icon> 
          上传到{{ currentView === 'team' ? '云端' : '本地' }}
        </el-button>
      </el-upload>
    </div>

    <el-alert
      v-if="currentView === 'personal' && showSafetyTip"
      title="⚠️ 安全提示： 数据仅存于当前浏览器..."
      type="warning"
      show-icon
      @close="handleCloseTip"
      style="margin-bottom: 20px; border-radius: 8px;"
    />

    <div class="gallery">
      <el-empty v-if="imageList.length === 0" description="这里空空如也，快去上传第一张素材吧！" />
      
      <div v-else class="image-grid">
        <el-card v-for="(img, index) in imageList" :key="index" class="image-card" shadow="hover" :body-style="{ padding: '0px' }">
          <el-image :src="img.url" fit="cover" class="image-preview" :preview-src-list="[img.url]" />
          
          <div class="image-info">
            <span class="image-name">素材 {{ index + 1 }}</span>
            
            <div class="actions">
              <el-tooltip content="提取灵感参数并重画">
                <el-button type="primary" size="small" circle plain @click="reuseInspiration(img)">
                  <el-icon><RefreshRight /></el-icon>
                </el-button>
              </el-tooltip>

              <el-button v-if="user.role === 'admin'" type="danger" size="small" circle plain @click="handleDelete(img)" style="margin-left: 5px;">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Delete, RefreshRight } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const currentView = ref('team')
const imageList = ref([])

const showSafetyTip = ref(sessionStorage.getItem('local_safety_tip_closed') !== 'true')

const handleCloseTip = () => {
  showSafetyTip.value = false
  sessionStorage.setItem('local_safety_tip_closed', 'true')
}

const user = JSON.parse(localStorage.getItem('jiuyu_user') || '{}')

const uploadData = computed(() => {
  return {
    asset_type: currentView.value,
    user_id: user.id || 1
  }
})


// 🔌 配置后端基准地址
const api = axios.create({ baseURL: 'http://127.0.0.1:8000' })

// 🛡️ 给信使加配：每次向后端发请求前，自动把本地保险箱里的 Token 掏出来举在头顶
api.interceptors.request.use(config => {
  const token = localStorage.getItem('jiuyu_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const fetchAssets = async () => {
  try {
    const response = await api.get('/assets', {
      params: {
        asset_type: currentView.value,
        user_id: user.id || 1
      }
    })
    if (response.data.status === 'success') {
      imageList.value = response.data.assets
    }
  } catch (error) {
    ElMessage.error('拉取历史素材失败，请检查网络')
  }
}

onMounted(() => {
  fetchAssets()
})

watch(currentView, () => {
  fetchAssets()
})

// 🌟 核心修改点：这里现在变得非常简洁，直接调用 fetchAssets 去数据库拿最新列表
const handleUploadSuccess = (response) => {
  if (response.status === 'success') {
    ElMessage.success(`上传成功！存储引擎：${response.storage}`)
    fetchAssets()
  } else {
    ElMessage.error(response.message || '上传失败，请重试')
  }
}

const handleUploadError = (err) => {
  ElMessage.error('上传请求被拒绝，请检查后端运行状态！')
}

// 💥 毁灭级操作：删除素材
const handleDelete = (asset) => {
  ElMessageBox.confirm(
    '此操作将把素材从数据库和硬盘/云端彻底粉碎，确定要继续吗？',
    '高危警告',
    {
      confirmButtonText: '执行粉碎',
      cancelButtonText: '手滑了',
      type: 'error',
    }
  ).then(async () => {
    try {
      const response = await api.delete(`/assets/${asset.id}`)
      if (response.data.status === 'success') {
        ElMessage.success(response.data.message)
        fetchAssets() // 重新拉取画廊，你会看到图片瞬间消失
      }
    } catch (error) {
      ElMessage.error('粉碎失败，请检查网络或查看后端报错')
    }
  }).catch(() => {
    // 点了取消，什么都不做
  })
}

// 💡 灵感回流：将参数打包存入缓存并跳转
const router = useRouter()
const reuseInspiration = (img) => {
  const reuseParams = {
    prompt: img.prompt || '',
    ratio: img.ratio || '1:1',
    style: img.style || 'none'
  }
  sessionStorage.setItem('jiuyu_reuse_params', JSON.stringify(reuseParams))
  router.push('/dashboard/drawing')
}
</script>

<style scoped>
.assets-container {
  padding: 10px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 15px 25px;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  margin-bottom: 20px;
}

.gallery {
  flex: 1;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  overflow-y: auto;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.image-card {
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.3s;
}

.image-card:hover {
  transform: translateY(-5px);
}

.image-preview {
  width: 100%;
  height: 200px;
  display: block;
  background-color: #f5f7fa;
}

.image-info {
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
}

.image-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}
</style>