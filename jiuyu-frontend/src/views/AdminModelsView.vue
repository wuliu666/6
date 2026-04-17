<template>
  <div class="flex h-full bg-gray-50 p-4 gap-4" style="min-height: 85vh;">
    <div class="w-64 bg-white p-4 rounded shadow-sm border">
      <div class="flex justify-between items-center mb-4">
        <h3 class="font-bold text-gray-700">API 渠道文件夹</h3>
        <el-button size="small" type="primary" @click="showChannelDialog = true" circle icon="Plus" />
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

    <div class="flex-1 bg-white p-6 rounded shadow-sm border relative">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-4">
          <h2 class="text-xl font-bold m-0">【{{ activeChannel }}】内容分拣</h2>
          <el-input v-model="searchQuery" placeholder="搜模型..." style="width: 200px" prefix-icon="Search" clearable />
        </div>
        <div class="flex gap-2">
          <el-button type="danger" plain size="small" @click="handleCleanLost" icon="Delete">清理失效</el-button>
          <el-button type="success" :loading="isSyncing" @click="handleSync" icon="Refresh">一键进货</el-button>
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
.batch-bar {
  background: #f0f9eb; border: 1px solid #c2e7b0; padding: 10px 20px;
  border-radius: 8px; margin-bottom: 15px; display: flex;
  justify-content: space-between; align-items: center;
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

const modelForm = ref({ id: null, model_name: '', channel_name: '', api_protocol: 'standard_openai', supported_ratios: [], supported_sizes: [] })

// 💡 联动逻辑
const getCount = (name) => allModels.value.filter(m => m.channel_name === name).length
const filteredModels = computed(() => {
  let list = allModels.value.filter(m => m.channel_name === activeChannel.value)
  if (searchQuery.value) list = list.filter(m => m.model_name.toLowerCase().includes(searchQuery.value.toLowerCase()))
  return list
})
const pagedModels = computed(() => filteredModels.value) // 后续可加分页逻辑

const fetchData = async () => {
  const [cRes, mRes] = await Promise.all([api.get('/admin/folders'), api.get('/admin/all-models')])
  channels.value = cRes.data.folders
  allModels.value = mRes.data.models
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
  // 💡 找回丢失的格式化逻辑
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
  const res = await api.post('/admin/sync-newapi')
  ElMessage.success(`进货成功：新增 ${res.data.new_count} 个`)
  fetchData()
  isSyncing.value = false
}

const deleteSingle = (id) => {
  ElMessageBox.confirm('彻底删除该记录？', '提示').then(async () => {
    await api.post('/admin/models/bulk-delete', { ids: [id] })
    fetchData()
  })
}

onMounted(fetchData)
</script>