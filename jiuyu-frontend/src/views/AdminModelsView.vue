<template>
  <div class="flex h-full bg-gray-50 p-4 gap-4" style="min-height: 85vh;">
    <div class="w-72 bg-white p-5 rounded-lg shadow-sm border-r">
      <div class="flex justify-between items-center mb-6 pb-2 border-b">
        <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wider">API 渠道管理</h3>
        <el-tooltip content="新建文件夹" placement="top">
          <el-button size="small" type="primary" @click="openNewChannelDialog" circle icon="Plus" />
        </el-tooltip>
      </div>
      <el-menu :default-active="activeChannel" @select="activeChannel = $event" class="border-none">
        <el-menu-item index="未分类">
          <span style="color:#e6a23c; font-weight:bold;">📥 未分类暂存池</span>
          <el-badge :value="getCount('未分类')" type="warning" class="ml-auto" />
        </el-menu-item>
        <el-menu-item v-for="c in channels" :key="c.name" :index="c.name">
          <span>📁 {{ c.name }}</span>
          <el-badge :value="getCount(c.name)" type="info" class="ml-auto" />
        </el-menu-item>
      </el-menu>
    </div>

    <div class="flex-1 bg-white p-6 rounded-lg shadow-sm border relative overflow-hidden">
      <div class="flex justify-between items-start mb-6">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <h2 class="text-2xl font-extrabold text-gray-800 m-0">{{ activeChannel }}</h2>
            <el-tag v-if="activeChannel === '未分类'" type="warning" effect="plain" size="small">系统暂存池</el-tag>
          </div>
          <div v-if="activeChannel !== '未分类'" class="flex gap-4 mt-2">
            <el-button size="small" type="primary" link icon="Edit" @click="editCurrentChannel">配置渠道密钥</el-button>
            <el-divider direction="vertical" />
            <el-button size="small" type="danger" link icon="Delete" @click="deleteCurrentChannel">解散此渠道</el-button>
          </div>
        </div>

        <div class="flex flex-col items-end gap-3">
          <div class="flex gap-2">
            <el-input v-model="searchQuery" placeholder="搜索模型名称..." style="width: 240px" prefix-icon="Search" clearable class="mr-2" />
            <el-button-group>
              <el-button type="danger" plain size="default" @click="handleCleanLost" icon="Delete">清理失效</el-button>
              <el-button type="primary" :loading="isSyncing" @click="handleSync" icon="Download">同步进货</el-button>
            </el-button-group>
          </div>
          <div class="text-xs text-gray-400">当前渠道共 {{ filteredModels.length }} 个模型可用</div>
        </div>
      </div>

      <transition name="el-zoom-in-top">
        <div v-if="selectedIds.length > 0" class="batch-bar">
          <el-tag type="primary" size="large">已选 {{ selectedIds.length }} 项</el-tag>
          <div class="flex gap-2">
            <el-select v-model="batchTargetChannel" placeholder="批量移动到..." size="small" style="width: 150px">
              <el-option v-for="c in channels" :key="c.name" :label="c.name" :value="c.name" />
            </el-select>
            <el-button type="primary" size="small" @click="handleBulkMove">确认移动</el-button>
            <el-button type="danger" size="small" @click="handleBulkDelete">批量物理删除</el-button>
          </div>
        </div>
      </transition>

      <el-table :data="pagedModels" border @selection-change="handleSelectionChange" style="width: 100%">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="model_name" label="模型 ID">
          <template #default="scope">
            <span :class="{ 'lost-model': scope.row.is_lost }">{{ scope.row.model_name }}</span>
            <el-tag v-if="scope.row.is_lost" type="danger" size="small" class="ml-2">失效</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="api_protocol" label="通讯协议" width="140">
          <template #default="scope">
            <el-tag :type="scope.row.api_protocol === 'standard_openai' ? 'success' : 'warning'">
              {{ scope.row.api_protocol === 'standard_openai' ? '标准' : 'Nano' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="scope">
            <el-button size="small" type="primary" link @click="editModel(scope.row)">配置</el-button>
            <el-button size="small" type="danger" link @click="deleteSingle(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showChannelDialog" :title="channelForm.isEdit ? '修改渠道配置' : '新建 API 渠道'" width="500px">
      <el-form :model="channelForm" label-position="top">
        <el-form-item label="渠道名称 (文件夹名)">
          <el-input v-model="channelForm.name" :disabled="channelForm.isEdit" placeholder="例如：某某中转站" />
        </el-form-item>
        <el-form-item label="Base URL (中转地址)">
          <el-input v-model="channelForm.base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="API Key (通讯令牌)">
          <el-input v-model="channelForm.api_key" placeholder="sk-..." type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChannelDialog = false">取消</el-button>
        <el-button type="primary" @click="saveChannel">保存设置</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showModelDialog" :title="'配置模型: ' + modelForm.model_name" width="550px">
      <el-form :model="modelForm" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="归属文件夹 (渠道)">
              <el-select v-model="modelForm.channel_name" class="w-full">
                <el-option label="📥 未分类暂存池" value="未分类" />
                <el-option v-for="c in channels" :key="c.name" :label="'📁 ' + c.name" :value="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="底层通讯协议">
              <el-select v-model="modelForm.api_protocol" class="w-full">
                <el-option label="✅ 标准 OpenAI" value="standard_openai" />
                <el-option label="⚠️ 特殊 Nano 直连" value="grsai_nano" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="🎨 该模型支持的画面比例">
          <el-checkbox-group v-model="modelForm.supported_ratios">
            <el-checkbox label="1:1" /> <el-checkbox label="4:3" />
            <el-checkbox label="16:9" /> <el-checkbox label="9:16" />
            <el-checkbox label="3:4" /> <el-checkbox label="2:3" />
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="📐 该模型支持的分辨率">
          <el-checkbox-group v-model="modelForm.supported_sizes">
            <el-checkbox label="1K" /> <el-checkbox label="2K" />
            <el-checkbox label="4K" /> <el-checkbox label="1024x1024" />
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModelDialog = false">取消</el-button>
        <el-button type="primary" @click="saveModel">保存并更新配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 优化：增加阴影和动画感，更像是一个浮动的工具栏 */
.batch-bar {
  background: #ecf5ff; 
  border: 1px solid #b3d8ff; 
  padding: 12px 24px;
  border-radius: 12px; 
  margin-bottom: 20px; 
  display: flex;
  justify-content: space-between; 
  align-items: center;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { transform: translateY(-10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
.lost-model { text-decoration: line-through; color: #909399; }
.ml-auto { margin-left: auto; }
.w-full { width: 100%; }
</style>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const api = axios.create({ baseURL: 'http://127.0.0.1:8000' })
api.interceptors.request.use(c => {
  const t = localStorage.getItem('jiuyu_token'); if(t) c.headers.Authorization = `Bearer ${t}`; return c
})

const channels = ref([])
const allModels = ref([])
const activeChannel = ref('未分类')
const searchQuery = ref('')
const selectedIds = ref([])
const batchTargetChannel = ref('')
const isSyncing = ref(false)
const showChannelDialog = ref(false)
const showModelDialog = ref(false)

// 💡 增加了渠道表单的数据结构
const channelForm = ref({ name: '', base_url: '', api_key: '', isEdit: false })
const modelForm = ref({ id: null, model_name: '', channel_name: '', api_protocol: 'standard_openai', supported_ratios: [], supported_sizes: [] })

// 💡 联动逻辑
const getCount = (name) => allModels.value.filter(m => m.channel_name === name).length
const filteredModels = computed(() => {
  let list = allModels.value.filter(m => m.channel_name === activeChannel.value)
  if (searchQuery.value) list = list.filter(m => m.model_name.toLowerCase().includes(searchQuery.value.toLowerCase()))
  return list
})
const pagedModels = computed(() => filteredModels.value) 

const fetchData = async () => {
  const [cRes, mRes] = await Promise.all([api.get('/admin/folders'), api.get('/admin/all-models')])
  channels.value = cRes.data.folders
  allModels.value = mRes.data.models
}

// 💡 新增：打开新建渠道弹窗
const openNewChannelDialog = () => {
  channelForm.value = { name: '', base_url: '', api_key: '', isEdit: false }
  showChannelDialog.value = true
}

// 💡 新增：编辑当前正在查看的渠道配置
const editCurrentChannel = () => {
  const current = channels.value.find(c => c.name === activeChannel.value)
  if (current) {
    channelForm.value = { ...current, isEdit: true }
    showChannelDialog.value = true
  }
}

// 💡 新增：保存渠道到后端
const saveChannel = async () => {
  if (!channelForm.value.name) return ElMessage.warning('渠道名称不能为空')
  await api.post('/admin/folders', channelForm.value)
  ElMessage.success('渠道配置保存成功！')
  showChannelDialog.value = false
  fetchData()
}

// 💡 新增：删除当前渠道（解散文件夹）
const deleteCurrentChannel = () => {
  ElMessageBox.confirm('确定解散该渠道吗？内部模型将退回未分类暂存池，不会丢失。', '解散警告', { type: 'warning' }).then(async () => {
    await api.delete(`/admin/folders/${activeChannel.value}`)
    ElMessage.success('渠道已解散！')
    activeChannel.value = '未分类'
    fetchData()
  })
}

// 💡 批量处理逻辑
const handleSelectionChange = (val) => { selectedIds.value = val.map(i => i.id) }
const handleBulkMove = async () => {
  if(!batchTargetChannel.value) return ElMessage.warning('请选择目标渠道')
  await api.post('/admin/models/bulk-update', { ids: selectedIds.value, channel_name: batchTargetChannel.value })
  ElMessage.success('批量搬运成功！')
  fetchData()
}
const handleBulkDelete = () => {
  ElMessageBox.confirm('确定要彻底抹除这些模型记录吗？', '警告', { type: 'error' }).then(async () => {
    await api.post('/admin/models/bulk-delete', { ids: selectedIds.value })
    ElMessage.success('批量清理完成')
    fetchData()
  })
}

const handleCleanLost = async () => {
  const res = await api.post('/admin/models/clean-lost')
  ElMessage.success(res.data.message)
  fetchData()
}

const editModel = (row) => {
  const ratios = typeof row.supported_ratios === 'string' ? JSON.parse(row.supported_ratios) : row.supported_ratios
  const sizes = typeof row.supported_sizes === 'string' ? JSON.parse(row.supported_sizes) : row.supported_sizes
  modelForm.value = { ...row, supported_ratios: ratios || [], supported_sizes: sizes || [] }
  showModelDialog.value = true
}

const saveModel = async () => {
  const payload = { ...modelForm.value }
  await api.post('/admin/model-configs/update', payload)
  ElMessage.success('配置已更新')
  showModelDialog.value = false
  fetchData()
}

const handleSync = async () => {
  isSyncing.value = true
  try {
    const res = await api.post('/admin/sync-newapi', { channel_name: activeChannel.value })
    // 💡 优化：把“失联数量”也展示出来，让管理员心里有数
    if (res.data.lost_count > 0) {
      ElMessage.warning(`进货完成：新增 ${res.data.new_count} 个，发现 ${res.data.lost_count} 个模型失联！`)
    } else {
      ElMessage.success(`定向进货成功：新增 ${res.data.new_count} 个`)
    }
    fetchData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '进货失败，请检查该渠道的 URL 和 Key')
  } finally {
    isSyncing.value = false
  }
}

const deleteSingle = (id) => {
  ElMessageBox.confirm('彻底删除该记录？', '提示').then(async () => {
    await api.post('/admin/models/bulk-delete', { ids: [id] })
    fetchData()
  })
}

onMounted(fetchData)
</script>