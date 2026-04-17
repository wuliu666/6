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
        <label>1. API 展示柜 (渠道) <el-tag size="small" type="success" v-if="Object.keys(groupedModels).length > 0">已连通</el-tag></label>
        <el-select v-model="drawParams.channel_name" placeholder="请先选择渠道" @change="handleProviderChange" style="width: 100%" :loading="isLoadingModels">
          <el-option v-for="key in Object.keys(groupedModels)" :key="key" :label="key" :value="key" />
        </el-select>
      </div>

      <div class="control-group">
        <label>2. 核心绘画引擎</label>
        <el-select v-model="drawParams.model" placeholder="请选择具体模型" style="width: 100%" :disabled="!drawParams.channel_name">
          <el-option v-for="m in currentChannelModels" :key="m" :label="m" :value="m" />
        </el-select>
      </div>

      <div class="control-group">
        <label>画面比例与清晰度</label>
        <div style="display: flex; gap: 10px;">
          <el-select v-model="drawParams.ratio" placeholder="画面比例":loading="isLoadingConfigs">
            <el-option 
              v-for="item in currentRatios" 
              :key="item.value" 
              :label="item.label" 
              :value="item.value" 
            />
          </el-select>

          <el-select v-model="drawParams.size" placeholder="清晰度尺寸":loading="isLoadingConfigs">
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
  channel_name: '',
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
const groupedModels = ref({}) // 👈 替换：存放渠道分组
const currentImage = ref('')  

// 💡 联动逻辑
const currentChannelModels = computed(() => {
  return groupedModels.value[drawParams.channel_name] || []
})

const handleProviderChange = () => {
  drawParams.model = ''
  if (currentChannelModels.value.length > 0) {
    drawParams.model = currentChannelModels.value[0]
  }
}    
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
      groupedModels.value = response.data.models
      const providers = Object.keys(groupedModels.value)
      if (providers.length > 0) {
        drawParams.channel_name = providers[0]
        drawParams.model = groupedModels.value[providers[0]][0] || ''
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

// 💡 优化三：新增配置加载状态，让下拉框更“稳”
const isLoadingConfigs = ref(false) 
const modelConfigs = ref({})

// 动态计算：双重 Key 防止串台
const currentRatios = computed(() => {
  const uniqueKey = `${drawParams.provider}::${drawParams.model}`
  const config = modelConfigs.value[uniqueKey]
  return config ? config.ratios : [{ label: '默认 1:1', value: '1:1' }] 
})

const currentSizes = computed(() => {
  const uniqueKey = `${drawParams.provider}::${drawParams.model}`
  const config = modelConfigs.value[uniqueKey]
  return config ? config.sizes : [{ label: '默认 1K', value: '1K' }]
})

// 💡 给小喇叭加一个“开机静音”开关
const allowNotify = ref(false)

// 💡 优化二：增加“贴心小喇叭”，自动修正时提醒用户
watch(currentRatios, (newRatios) => {
  if (newRatios && newRatios.length > 0) {
    const isExist = newRatios.some(r => r.value === drawParams.ratio)
    if (!isExist) {
      const oldVal = drawParams.ratio
      drawParams.ratio = newRatios[0].value || newRatios[0]
      // 只有静音开关打开时，才允许弹窗！
      if (oldVal && allowNotify.value) {
        ElMessage.info({ message: `当前模型不支持 ${oldVal}，已自动切换为兼容比例`, duration: 2000 })
      }
    }
  }
}, { immediate: true })

watch(currentSizes, (newSizes) => {
  if (newSizes && newSizes.length > 0) {
    const isExist = newSizes.some(s => s.value === drawParams.size)
    if (!isExist) {
      const oldVal = drawParams.size
      drawParams.size = newSizes[0].value || newSizes[0]
      // 只有静音开关打开时，才允许弹窗！
      if (oldVal && allowNotify.value) {
        ElMessage.info({ message: `当前模型不支持 ${oldVal}，已自动匹配最佳分辨率`, duration: 2000 })
      }
    }
  }
}, { immediate: true })
// ==========================================

// 💡 优化一：增加“长久记忆” (localStorage)，实现秒开体验
const fetchModelConfigs = async () => {
  // 先从保险箱看一眼有没有旧记忆，有的话先用上，不等后台
  const saved = localStorage.getItem('jiuyu_model_configs')
  if (saved) modelConfigs.value = JSON.parse(saved)

  isLoadingConfigs.value = true
  try {
    const res = await api.get('/drawing/model-configs')
    if (res.data.status === 'success') {
      modelConfigs.value = res.data.configs
      // 拿到最新的，赶紧更新一下保险箱里的记忆
      localStorage.setItem('jiuyu_model_configs', JSON.stringify(res.data.configs))
    }
  } catch (error) {
    console.error('拉取模型动态配置失败', error)
  } finally {
    isLoadingConfigs.value = false
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
      if (params.style) drawParams.style = params.style
      
      // ⚠️ 极其关键的第一步：先恢复“模型”，让网页的“比例下拉框”先变过来
      if (params.model) drawParams.model = params.model
      
      // ⚠️ 极其关键的第二步：稍微等 50 毫秒（错峰填表），等网页准备好了，再填入比例和尺寸
      setTimeout(() => {
        if (params.ratio) drawParams.ratio = params.ratio
        if (params.size) drawParams.size = params.size
      }, 50)
      
      sessionStorage.removeItem('jiuyu_reuse_params') // 阅后即焚
      ElMessage.success('🪄 已为您还原历史灵感参数！')
    } catch (e) {}
  }

  // 💡 核心修复：在页面数据全部初始化完毕后，延迟 1 秒再把小喇叭的“静音”取消掉
  setTimeout(() => {
    allowNotify.value = true
  }, 1000)
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
      provider: drawParams.provider, // 👈 发送渠道标识
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
        size: drawParams.size,       // 💡 补上遗漏的尺寸
        model: drawParams.model,     // 💡 补上遗漏的模型
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
    formData.append('size', drawParams.size)      // 💡 补上遗漏的尺寸
    formData.append('model', drawParams.model)    // 💡 补上遗漏的模型
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