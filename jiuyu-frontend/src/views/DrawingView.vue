<template>
  <div class="drawing-container">
    <div class="control-panel">
      <h3 class="panel-title">✨ 灵感咒语</h3>
      
      <div class="control-group">
        <label>画面描述 (Prompt)</label>
        <el-input
          v-model="drawParams.prompt"
          type="textarea"
          :rows="4"
          placeholder="描述你想要的画面，例如：一个赛博朋克风格的未来城市，霓虹灯，下雨，4k 高清..."
          resize="none"
        />
      </div>

      <div class="control-group">
        <label>核心绘画引擎 <el-tag size="small" type="success" v-if="availableModels.length > 0">已连通网关</el-tag></label>
        <el-select v-model="drawParams.model" placeholder="正在加载模型..." style="width: 100%" :loading="isLoadingModels">
          <el-option 
            v-for="modelName in availableModels" 
            :key="modelName" 
            :label="modelName" 
            :value="modelName" 
          />
        </el-select>
      </div>

      <div class="control-group">
        <label>画面比例与清晰度</label>
        <div style="display: flex; gap: 10px;">
          <el-select v-model="drawParams.ratio" placeholder="比例" style="flex: 1;">
            <el-option label="智能 (Auto)" value="auto" />
            <el-option label="1:1 (头像)" value="1:1" />
            <el-option label="16:9 (电脑横屏)" value="16:9" />
            <el-option label="9:16 (手机竖屏)" value="9:16" />
            <el-option label="21:9 (宽幅电影)" value="21:9" />
            <el-option label="3:4" value="3:4" />
          </el-select>
          <el-select v-model="drawParams.size" placeholder="清晰度" style="flex: 1;">
            <el-option label="高清 2K" value="2K" />
            <el-option label="超清 4K" value="4K" />
          </el-select>
        </div>
      </div>

      <div class="control-group">
        <label>参考垫图 (最多10张)</label>
        <el-upload
          action="#"
          list-type="picture-card"
          :auto-upload="false"
          :on-change="handleImageUpload"
          :show-file-list="false"
          class="reference-upload"
        >
          <div style="display: flex; flex-direction: column; align-items: center; color: #909399;">
            <span style="font-size: 24px; font-weight: 300;">+</span>
          </div>
        </el-upload>
        
        <div v-if="drawParams.referenceImages.length > 0" class="upload-preview-container">
          <div v-for="(img, index) in drawParams.referenceImages" :key="index" class="preview-item">
            <el-image :src="img" fit="cover" />
            <div class="preview-delete" @click.stop="removeReferenceImage(index)" title="移除此垫图">
              ✕
            </div>
          </div>
        </div>
      </div>

      <div class="control-group">
        <label>艺术风格</label>
        <el-select v-model="drawParams.style" placeholder="选择风格" style="width: 100%">
          <el-option label="🎨 不限定 (由大模型自由发挥)" value="none" />
          <el-option label="🌸 二次元 (Anime)" value="anime" />
          <el-option label="📸 真实摄影 (Photorealistic)" value="photo" />
          <el-option label="🖌️ 3D 渲染 (3D Render)" value="3d" />
        </el-select>
      </div>

      <el-button 
        type="primary" 
        size="large" 
        class="generate-btn" 
        @click="handleGenerate"
        :loading="isGenerating"
      >
        <el-icon class="el-icon--left" v-if="!isGenerating"><MagicStick /></el-icon>
        {{ isGenerating ? 'AI 正在极速绘制中...' : '立即生成画面' }}
      </el-button>
    </div>

    <div class="canvas-panel" v-loading="isGenerating" element-loading-text="大模型正在疯狂计算像素...">
      <el-empty 
        v-if="!currentImage" 
        description="灵感画板已就绪，等待你的咒语召唤..." 
        :image-size="200"
      />
      
      <div v-else class="result-display">
        <el-image 
          :src="currentImage" 
          fit="contain" 
          class="generated-image"
          :preview-src-list="[currentImage]"
        />
        <div class="image-actions">
          <el-button type="success" plain round @click="saveToAssets">
            <el-icon class="el-icon--left"><Download /></el-icon> 存入我的素材库
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: 'http://127.0.0.1:8000' })
api.interceptors.request.use(config => {
  const token = localStorage.getItem('jiuyu_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const drawParams = reactive({
  prompt: '',
  ratio: '16:9',
  size: '2K',
  style: 'none',
  model: '',
  referenceImages: [] 
})


// 🚀 发送请求时
const submitDraw = async () => {
  const response = await fetch('http://localhost:8000/drawing/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // 'Authorization': `Bearer ${token}` 记得带上你系统里的 token
    },
    // 把所有的参数完整发给咱们自己的后端！
    body: JSON.stringify(drawParams.value) 
  });
  // ... 处理返回结果
}

const isGenerating = ref(false)
const isLoadingModels = ref(false) 
const availableModels = ref([])    
const currentImage = ref('')       

// ==========================================
// 📸 垫图转 Base64 逻辑引擎 (复刻自旧版)
// ==========================================
const handleImageUpload = (uploadFile) => {
  if (drawParams.referenceImages.length >= 10) {
    ElMessage.warning('⚠️ 最多只能上传 10 张图片作为参考垫图！')
    return false
  }
  if (!uploadFile.raw.type.startsWith('image/')) {
    ElMessage.warning('请上传合法的图片文件！')
    return false
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    drawParams.referenceImages.push(e.target.result)
  }
  reader.readAsDataURL(uploadFile.raw)
  return false // 拦截 Element Plus 的默认网络上传
}

const removeReferenceImage = (index) => {
  drawParams.referenceImages.splice(index, 1)
}

// ==========================================
// 🚀 核心黑科技：浏览器本地 IndexedDB 引擎
// ==========================================
const LOCAL_DB_NAME = 'NineRainLocalAssetsDB'

// 初始化或打开本地数据库
const saveToLocalDB = (asset) => {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(LOCAL_DB_NAME, 1)
    
    // 如果是第一次建库，创建一张叫 'assets' 的表
    req.onupgradeneeded = e => {
      const db = e.target.result
      if (!db.objectStoreNames.contains('assets')) {
        db.createObjectStore('assets', { keyPath: 'id' })
      }
    }
    
    req.onsuccess = e => {
      const db = e.target.result
      const tx = db.transaction('assets', 'readwrite')
      const store = tx.objectStore('assets')
      store.put(asset) // 存入数据
      tx.oncomplete = () => resolve(true)
      tx.onerror = () => reject(tx.error)
    }
    req.onerror = () => reject(req.error)
  })
}
// ==========================================

const fetchModels = async () => {
  isLoadingModels.value = true
  try {
    const response = await api.get('/drawing/models')
    if (response.data.status === 'success') {
      availableModels.value = response.data.models
      if (availableModels.value.length > 0) {
        drawParams.model = availableModels.value[0]
      }
    }
  } catch (error) {
    // 💡 核心：把真正的死因打印在控制台，并在页面右上角弹窗！
    const errorMsg = error.response?.data?.detail || error.message || '未知网络错误'
    console.error("❌ 模型菜单拉取失败详情：", errorMsg)
    ElMessage.error(`菜单拉取失败: ${errorMsg}`)
  } finally {
    isLoadingModels.value = false
  }
}

onMounted(() => {
  fetchModels()
  
})

const handleGenerate = async () => {
  if (!drawParams.prompt.trim()) {
    ElMessage.warning('咒语不能为空哦！')
    return
  }
  if (!drawParams.model) {
    ElMessage.warning('请先选择一个核心绘画引擎！')
    return
  }

  isGenerating.value = true
  currentImage.value = '' 

  try {
    const response = await api.post('/drawing/generate', {
      prompt: drawParams.prompt,
      ratio: drawParams.ratio,
      style: drawParams.style,
      model: drawParams.model 
    })
    
    if (response.data.status === 'success') {
      currentImage.value = response.data.image_url
      ElMessage.success('🎉 绝密画作生成完毕！')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '网络波动，大模型连接失败')
  } finally {
    isGenerating.value = false 
  }
}

// ==========================================
// 🚀 零成本入库：将图片打包进浏览器的私密空间
// ==========================================
const saveToAssets = async () => {
  if (!currentImage.value) {
    ElMessage.warning('请先生成一张画作再保存哦！')
    return
  }

  try {
    ElMessage.info('📥 正在进行本地私密化存储...')
    
    // 1. 从网络上把图片抓取到前端内存中
    const res = await fetch(currentImage.value)
    const blob = await res.blob()
    
    // 2. 将图片转换为 Base64 文本格式 (这是 IndexedDB 最喜欢的格式)
    const reader = new FileReader()
    reader.onloadend = async () => {
      const base64data = reader.result
      
      // 3. 构建你在旧版中设计的数据结构
      const assetObj = {
        id: 'local_asset_' + Date.now().toString(36), // 生成唯一ID
        title: `AI灵感_${new Date().toLocaleTimeString('zh-CN', {hour12:false})}`,
        type: 'image',
        prompt: drawParams.prompt,
        image: base64data,     // 原图存本地
        thumb: base64data,     // 缩略图存本地
        library_mode: 'personal',
        created_at: Date.now(),
        // 绑定当前用户，即使换账号登录，本地数据也能根据账号隔离
        uploader_key: localStorage.getItem('jiuyu_token') || 'Creator' 
      }

      // 4. 写入浏览器的 IndexedDB！
      await saveToLocalDB(assetObj)
      ElMessage.success('🎉 灵感已成功封入本地浏览器！0服务器占用！')
    }
    
    // 启动读取
    reader.readAsDataURL(blob)

  } catch (error) {
    console.error(error)
    ElMessage.error('本地存储失败，可能是浏览器安全策略拦截了图片拉取。')
  }
}


</script>

<style scoped>
.drawing-container {
  display: flex;
  height: calc(100vh - 100px);
  gap: 20px;
  padding: 10px;
}

/* 左侧控制台样式 */
.control-panel {
  width: 320px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}

.panel-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 18px;
  color: #303133;
}

.control-group {
  margin-bottom: 20px;
}

.control-group label {
  display: block;
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.generate-btn {
  margin-top: auto; /* 把按钮顶到最下面 */
  width: 100%;
  border-radius: 8px;
  font-size: 16px;
  font-weight: bold;
}

/* 右侧画板样式 */
.canvas-panel {
  flex: 1;
  background: #f5f7fa; /* 稍微深一点的背景，衬托图片 */
  border-radius: 12px;
  box-shadow: inset 0 2px 12px 0 rgba(0,0,0,0.02);
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  border: 2px dashed #e4e7ed;
}

.result-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  height: 100%;
  padding: 20px;
}

.generated-image {
  max-width: 100%;
  max-height: calc(100% - 60px); /* 留出底部按钮的空间 */
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  transition: transform 0.3s;
}

.generated-image:hover {
  transform: scale(1.02);
}

.image-actions {
  margin-top: 20px;
}
</style>