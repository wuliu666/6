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
          <el-select v-model="drawParams.ratio" placeholder="画面比例">
            <el-option 
              v-for="item in currentRatios" 
              :key="item.value" 
              :label="item.label" 
              :value="item.value" 
            />
          </el-select>

          <el-select v-model="drawParams.size" placeholder="清晰度尺寸">
            <el-option 
              v-for="item in currentSizes" 
              :key="item.value" 
              :label="item.label" 
              :value="item.value" 
            />
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
        <div class="image-actions" v-if="currentImage">
        
        
        <el-button type="success" @click="saveToAssets">上传个人素材库</el-button>

        <el-button 
          v-if="userRole === 'admin'" 
          type="warning" 
          @click="saveToTeamAssets"
        >
          上传团队素材库
        </el-button>
      </div>
      </div>
    </div>
  </div>
</template>



<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
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
const userRole = ref('user') // 💡 新增：记录当前用户的角色权限 

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

const modelConfigs = ref({})

// 动态计算：根据当前选择的模型，自动过滤出它支持的比例
const currentRatios = computed(() => {
  const config = modelConfigs.value[drawParams.model]
  return config ? config.ratios : [{ label: '默认 1:1', value: '1:1' }] 
})

// 动态计算：根据当前选择的模型，自动过滤出它支持的清晰度
const currentSizes = computed(() => {
  const config = modelConfigs.value[drawParams.model]
  return config ? config.sizes : [{ label: '默认 1K', value: '1K' }]
})

// ==========================================
// 💡 神仙代码：监听比例和尺寸变化，自动修正“幽灵残影”！
// ==========================================
watch(currentRatios, (newRatios) => {
  if (newRatios && newRatios.length > 0) {
    // 检查画板当前的比例，还在不在最新的可选列表里
    const isExist = newRatios.some(r => r.value === drawParams.ratio)
    if (!isExist) {
      // 如果不在了（比如后台没配16:9），就强制把它变成新列表里的第一个！
      drawParams.ratio = newRatios[0].value || newRatios[0]
    }
  }
}, { immediate: true })

watch(currentSizes, (newSizes) => {
  if (newSizes && newSizes.length > 0) {
    const isExist = newSizes.some(s => s.value === drawParams.size)
    if (!isExist) {
      drawParams.size = newSizes[0].value || newSizes[0]
    }
  }
}, { immediate: true })
// ==========================================

// 💡 拉取配置的函数
const fetchModelConfigs = async () => {
  try {
    const res = await api.get('/drawing/model-configs')
    if (res.data.status === 'success') {
      modelConfigs.value = res.data.configs
    }
  } catch (error) {
    console.error('拉取模型动态配置失败', error)
  }
}
// ==========================================

onMounted(() => {
  fetchModels()
  fetchModelConfigs()
  
  // 💡 1. 身份识别
  try {
    const userStr = localStorage.getItem('jiuyu_user')
    if (userStr) {
      const user = JSON.parse(userStr)
      userRole.value = user.role || 'user'
    }
  } catch (e) {
    console.error('解析角色权限失败', e)
  }

  // 💡 2. 解决刷新丢失
  const savedDraft = sessionStorage.getItem('jiuyu_draft_image')
  if (savedDraft) {
    currentImage.value = savedDraft
  }

  // 💡 3. 核心：接收从素材库传回来的灵感参数
  const reuseData = sessionStorage.getItem('jiuyu_reuse_params')
  if (reuseData) {
    try {
      const params = JSON.parse(reuseData)
      drawParams.prompt = params.prompt || ''
      if (params.ratio) drawParams.ratio = params.ratio
      if (params.style) drawParams.style = params.style
      
      sessionStorage.removeItem('jiuyu_reuse_params') // 阅后即焚
      ElMessage.success('🪄 已为您还原历史灵感参数！')
    } catch (e) {}
  }
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
    // 数据透传给 FastAPI
    const response = await api.post('/drawing/generate', {
      prompt: drawParams.prompt,
      model: drawParams.model,
      aspectRatio: drawParams.ratio,
      imageSize: drawParams.size,
      style: drawParams.style,
      urls: drawParams.referenceImages 
    })
    
    if (response.data.status === 'success') {
      currentImage.value = response.data.image_url
      // 💡 记录到会话缓存，这样刷新页面后 onMounted 就能把它抓回来展示
      sessionStorage.setItem('jiuyu_draft_image', response.data.image_url)
      ElMessage.success('🎉 绝密画作生成完毕！')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '网络波动，大模型连接失败')
  } finally {
    isGenerating.value = false 
  }
}

// ==========================================
// 🔒 真正的不动库：个人素材存入【用户本地电脑硬盘】(IndexedDB)
// ==========================================
const saveToAssets = async () => {
  if (!currentImage.value) {
    ElMessage.warning('请先生成一张画作再保存哦！')
    return
  }

  try {
    ElMessage.info('📥 正在存入您的本地电脑硬盘...')
    
    const res = await fetch(currentImage.value)
    const blob = await res.blob()
    
    const reader = new FileReader()
    reader.onloadend = async () => {
      // 构建包含参数的本地数据包
      const assetObj = {
        id: 'local_' + Date.now(),
        url: reader.result, // 图片转 Base64 存在本地
        prompt: drawParams.prompt,
        ratio: drawParams.ratio,
        style: drawParams.style,
        created_at: Date.now()
      }
      
      // 调用文件上方你已经写好的 saveToLocalDB
      await saveToLocalDB(assetObj)
      ElMessage.success('🎉 个人素材已存入本地浏览器，服务器 0 占用！')
    }
    reader.readAsDataURL(blob)
  } catch (error) {
    console.error('本地入库失败:', error)
    ElMessage.error('本地存储失败，请检查浏览器权限。')
  }
}

// ==========================================
// 👑 管理员专供：将灵感上传至团队共享库 (asset_type: 'team')
// ==========================================
const saveToTeamAssets = async () => {
  if (!currentImage.value) {
    ElMessage.warning('请先生成一张画作再上传哦！')
    return
  }

  try {
    ElMessage.info('📡 正在将作品同步至团队共享库...')
    
    // 1. 获取图片文件流
    const res = await fetch(currentImage.value)
    const blob = await res.blob()
    
    // 2. 构建上传包 (这里告诉后端资产类型是 team)
    const formData = new FormData()
    const filename = `Team_Asset_${Date.now()}.png`
    formData.append('file', blob, filename)
    formData.append('asset_type', 'team') // 👉 核心分发标识
    // 💡 将画板当前的参数一同打包发给后端
    formData.append('prompt', drawParams.prompt)
    formData.append('ratio', drawParams.ratio)
    formData.append('style', drawParams.style)
    // 💡 新增：把当前画板的参数一起发给后端，后端会将它转存到 COS
    const userStr = localStorage.getItem('jiuyu_user')
    const userId = userStr ? JSON.parse(userStr).id : 1
    formData.append('user_id', userId)

    // 3. 发送给 FastAPI 后端
    const uploadRes = await api.post('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (uploadRes.data.status === 'success') {
      ElMessage.success('🎉 团队素材上传成功！所有成员均可在素材库查看。')
    } else {
      ElMessage.error(uploadRes.data.message || '上传失败')
    }
  } catch (error) {
    console.error('上传团队库失败:', error)
    ElMessage.error('上传失败，请检查网络连接或管理员权限。')
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