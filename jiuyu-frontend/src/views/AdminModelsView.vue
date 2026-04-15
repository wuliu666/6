<template>
  <div class="admin-container">
    <div class="header-section">
      <h2>⚙️ 九雨模型能力控制台</h2>
      <p class="subtitle">在这里为绘图模型分配“超能力”，设置后全站生图板将实时同步选项。</p>
    </div>

    <div class="config-card">
      <el-form label-position="top">
        <el-form-item label="1. 选择或输入模型标识 (Model ID)">
          <el-select
            v-model="currentConfig.model_name"
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入模型名称，如 nano-banana-2"
            class="full-width"
          >
            <el-option
              v-for="model in allModels"
              :key="model.id"
              :label="model.id"
              :value="model.id"
            />
          </el-select>
          <div class="form-tip">提示：您可以直接从下拉框选择网关已有的模型，也可以手动输入新模型名。</div>
        </el-form-item>

        <el-form-item label="2. 标记模型属性">
          <el-radio-group v-model="currentConfig.is_image_model" size="large">
            <el-radio-button :label="false">💬 对话模型</el-radio-button>
            <el-radio-button :label="true">🎨 绘图模型</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <transition name="el-fade-in-linear">
          <div v-if="currentConfig.is_image_model" class="image-params-box">
            <el-divider content-position="left">绘图能力配置 (多选打勾)</el-divider>

            <el-form-item label="支持的画面比例 (Aspect Ratios)">
              <el-checkbox-group v-model="selectedRatios" class="checkbox-grid">
                <el-checkbox 
                  v-for="item in predefinedRatios" 
                  :key="item.value" 
                  :label="item"
                  border
                >
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item label="支持的分辨率/尺寸 (Image Sizes)">
              <el-checkbox-group v-model="selectedSizes" class="checkbox-grid">
                <el-checkbox 
                  v-for="item in predefinedSizes" 
                  :key="item.value" 
                  :label="item"
                  border
                >
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </div>
        </transition>

        <el-form-item style="margin-top: 40px;">
          <el-button type="primary" size="large" icon="Promotion" @click="saveConfig" :loading="loading">
            一键同步至全站数据库
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../main' // 确保指向你的 axios 实例

// --- 预设模板字典 (你想加什么，直接在下面数组里添一行即可) ---
const predefinedRatios = [
  { label: '1:1 正方', value: '1:1' },
  { label: '16:9 横屏', value: '16:9' },
  { label: '9:16 竖屏', value: '9:16' },
  { label: '4:3 传统横', value: '4:3' },
  { label: '3:4 传统竖', value: '3:4' },
  { label: '21:9 带鱼屏', value: '21:9' }
]

const predefinedSizes = [
  { label: '标清 1K', value: '1K' },
  { label: '高清 2K', value: '2K' },
  { label: '超清 4K', value: '4K' },
  { label: '标准 1024', value: '1024x1024' },
  { label: '超清 2048', value: '2048x2048' }
]

// --- 响应式数据 ---
const allModels = ref([]) // 存储从网关拉取的原始模型列表
const loading = ref(false)
const currentConfig = ref({
  model_name: '',
  is_image_model: true
})

const selectedRatios = ref([])
const selectedSizes = ref([])

// --- 逻辑函数 ---

// 1. 获取所有模型列表 (用于下拉框选择)
const fetchAllModels = async () => {
  try {
    const res = await api.get('/drawing/models') // 调用你现有的拉取接口
    allModels.value = res.data
  } catch (err) {
    console.error('模型列表拉取失败')
  }
}

// 2. 保存配置到后端数据库
const saveConfig = async () => {
  if (!currentConfig.value.model_name) return ElMessage.warning('请输入模型名称')
  
  loading.value = true
  const payload = {
    model_name: currentConfig.value.model_name,
    is_image_model: currentConfig.value.is_image_model,
    supported_ratios: selectedRatios.value,
    supported_sizes: selectedSizes.value
  }

  try {
    const res = await api.post('/admin/model-configs/update', payload)
    if (res.data.status === 'success') {
      ElMessage.success(res.data.message)
    }
  } catch (err) {
    ElMessage.error('同步失败，请检查后端 API')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAllModels()
})
</script>

<style scoped>
.admin-container {
  padding: 30px;
  max-width: 1000px;
  margin: 0 auto;
}
.header-section {
  margin-bottom: 30px;
}
.subtitle {
  color: #888;
  font-size: 14px;
}
.config-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}
.full-width {
  width: 100%;
}
.form-tip {
  font-size: 12px;
  color: #b0b0b0;
  margin-top: 5px;
}
.image-params-box {
  background: #f9fafc;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
}
.checkbox-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.el-checkbox.is-bordered {
  margin-left: 0 !important;
  margin-right: 10px;
  margin-bottom: 10px;
}
</style>