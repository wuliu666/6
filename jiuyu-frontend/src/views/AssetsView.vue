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

    <div class="gallery" v-infinite-scroll="loadMore" :infinite-scroll-distance="200">
      <el-empty v-if="displayList.length === 0" description="这里空空如也，快去上传第一张素材吧！" />
      
      <div v-else class="image-grid">
        <el-card 
          v-for="(img, index) in displayList" 
          :key="index" class="image-card" shadow="hover" :body-style="{ padding: '0px' }">
          
          <el-image :src="getThumbUrl(img)" fit="cover" class="image-preview" :preview-src-list="[img.url]" lazy>
            <template #placeholder>
              <div class="image-skeleton">
                <img v-if="img.blur_hash" :src="img.blur_hash" class="blur-placeholder" />
                <span v-else class="loading-text">光速加载中...</span>
              </div>
            </template>
          </el-image>
          
          <div class="image-info">
            <el-tooltip :content="img.prompt || '外部上传，无参数'" placement="top" :show-after="500">
              <span class="image-name" style="cursor: pointer; width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {{ img.prompt || '未记录参数' }}
              </span>
            </el-tooltip>
            
            <div class="actions">
              <el-tooltip content="提取灵感参数并重画">
                <el-button type="primary" size="small" circle plain @click="reuseInspiration(img)">
                  <el-icon><RefreshRight /></el-icon>
                </el-button>
              </el-tooltip>

              <el-button v-if="currentView === 'personal' || user.role === 'admin'" type="danger" size="small" circle plain @click="handleDelete(img)" style="margin-left: 5px;">
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
// 💡 绝杀技 3 核心：双数组截流引擎
const imageList = ref([])     // 蓄水池：存放从数据库拉来的 10000 张图的数据 (只占内存，不耗 CPU)
const displayList = ref([])   // 展示区：只存放屏幕上要渲染的卡片
const pageSize = 30           // 每次往下划，释放 30 张图出来
let currentPage = 1           // 当前切片游标

// 滑动到底部时自动触发的函数
const loadMore = () => {
  if (displayList.value.length >= imageList.value.length && imageList.value.length > 0) return
  const start = (currentPage - 1) * pageSize
  const end = currentPage * pageSize
  const nextBatch = imageList.value.slice(start, end)
  if (nextBatch.length > 0) {
    displayList.value.push(...nextBatch)
    currentPage++
  }
}

const fetchAssets = async () => {
  // 每次刷新或切换 Tab，彻底清空水池和展示区
  imageList.value = [] 
  displayList.value = []
  currentPage = 1
  
  if (currentView.value === 'personal') {
    const req = indexedDB.open('NineRainLocalAssetsDB', 1)
    req.onsuccess = e => {
      const db = e.target.result
      if (!db.objectStoreNames.contains('assets')) return
      const store = db.transaction('assets', 'readonly').objectStore('assets')
      store.getAll().onsuccess = (ev) => {
        imageList.value = ev.target.result.reverse()
        loadMore() // 💡 数据就位，立刻释放第一批 30 张图上屏幕！
      }
    }
    req.onerror = () => { ElMessage.error('无法读取本地私密素材库') }
  } else {
    try {
      const response = await api.get('/assets', {
        params: { asset_type: 'team', user_id: user.id || 1 }
      })
      if (response.data.status === 'success') {
        imageList.value = response.data.assets
        loadMore() // 💡 数据就位，立刻释放第一批 30 张图上屏幕！
      }
    } catch (error) {
      ElMessage.error('拉取团队素材失败，请检查网络')
    }
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

// 💥 毁灭级操作：删除素材 (智能双擎判断)
const handleDelete = (asset) => {
  ElMessageBox.confirm(
    '此操作将把素材彻底粉碎，确定要继续吗？',
    '高危警告',
    {
      confirmButtonText: '执行粉碎',
      cancelButtonText: '手滑了',
      type: 'error',
    }
  ).then(async () => {
    try {
      // 💡 智能判断：如果当前是个人素材页面，去删本地 IndexedDB
      if (currentView.value === 'personal') {
        const req = indexedDB.open('NineRainLocalAssetsDB', 1)
        req.onsuccess = e => {
          const db = e.target.result
          const tx = db.transaction('assets', 'readwrite')
          tx.objectStore('assets').delete(asset.id)
          tx.oncomplete = () => {
            ElMessage.success('🗑️ 本地私密素材已粉碎')
            fetchAssets() // 重新刷新列表
          }
        }
      } 
      // 💡 否则：向后端发送请求，删除服务器/云端的团队素材
      else {
        const response = await api.delete(`/assets/${asset.id}`)
        if (response.data.status === 'success') {
          ElMessage.success(response.data.message)
          fetchAssets() 
        }
      }
    } catch (error) {
      ElMessage.error('粉碎失败，请检查网络或查看后端报错')
    }
  }).catch(() => {})
}

// 💡 灵感回流：将参数打包存入缓存并跳转
const router = useRouter()
const reuseInspiration = (img) => {
  const reuseParams = {
    prompt: img.prompt || '',
    ratio: img.ratio || img.aspectRatio || '1:1', 
    size: img.size || img.imageSize || '1024x1024', 
    style: img.style || 'none',
    model: img.model || '' 
  }
  sessionStorage.setItem('jiuyu_reuse_params', JSON.stringify(reuseParams))
  // 💡 核心修复：必须带上 /dashboard 父级路径，否则会白屏
  router.push('/dashboard/drawing') 
}

// 💡 绝杀技 1：云端动态切图引擎 (借助腾讯云数据万象，一毫秒极速切出微小 WebP)
const getThumbUrl = (img) => {
  if (!img || !img.url) return ''
  if (img.storage === 'TENCENT_COS' || img.url.includes('myqcloud.com')) {
    return `${img.url}?imageMogr2/thumbnail/400x/format/webp/interlace/1`
  }
  return img.url // 本地图片 0 延迟，直接返回
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
  
  /* 💡 大厂底层黑科技：原生 DOM 节点回收 */
  content-visibility: auto;      /* 只要这张卡片滚出屏幕，浏览器自动卸载它的渲染计算 */
  contain-intrinsic-size: 250px; /* 告诉浏览器卸载后给它保留个 250px 的空气占位，防止滚动条乱跳 */
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

/* 💡 绝杀技 2：骨架屏专属视觉特效 */
.image-skeleton {
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  overflow: hidden;
  position: relative;
}

.blur-placeholder {
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* 魔法核心：让显卡全速运转，瞬间生成极其丝滑的高斯模糊 */
  filter: blur(15px); 
  /* 稍微放大一点，防止模糊后边缘缩进漏出难看的白底边框 */
  transform: scale(1.1); 
}

.loading-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #909399;
  font-size: 12px;
}
</style>