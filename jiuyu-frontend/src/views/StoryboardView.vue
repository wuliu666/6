<template>
  <div class="storyboard-container">
    <el-scrollbar class="chat-history" ref="scrollbarRef">
      <div class="message-list">
        <div class="message-item assistant">
          <el-avatar class="avatar" :size="40" style="background: #409EFF">AI</el-avatar>
          <div class="msg-bubble">你好！我是九雨分镜生成助手。请告诉我你的剧情大纲，我来帮你拆解分镜。</div>
        </div>

        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message-item', msg.role]"
        >
          <el-avatar v-if="msg.role === 'assistant'" class="avatar" :size="40" style="background: #409EFF">AI</el-avatar>
          <el-avatar v-else class="avatar" :size="40" style="background: #67C23A">我</el-avatar>
          <div class="msg-bubble">{{ msg.content }}</div>
        </div>
      </div>
    </el-scrollbar>

    <div class="input-area">
      <el-input
        v-model="inputContent"
        type="textarea"
        :rows="3"
        placeholder="输入剧情，例如：主角推开沉重的大门，阳光刺眼..."
        resize="none"
        @keydown.enter.prevent="handleSend"
      />
      <div class="action-bar">
        <span class="hint">按 Enter 发送，Shift + Enter 换行</span>
        <el-button type="primary" :loading="isGenerating" @click="handleSend" round>
          {{ isGenerating ? '生成中...' : '发送指令 (Enter)' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const inputContent = ref('')
const messages = ref([])
const isGenerating = ref(false)
const scrollbarRef = ref(null)

// 自动滚动到底部的函数
const scrollToBottom = () => {
  nextTick(() => {
    if (scrollbarRef.value) {
      scrollbarRef.value.setScrollTop(99999)
    }
  })
}

// 核心发送逻辑 (处理 SSE 流式输出)
const handleSend = async () => {
  if (!inputContent.value.trim() || isGenerating.value) return

  const userText = inputContent.value.trim()
  messages.value.push({ role: 'user', content: userText })
  inputContent.value = ''
  scrollToBottom()

  isGenerating.value = true
  
  // 先在屏幕上放一个空的 AI 气泡，准备接收打字机数据
  messages.value.push({ role: 'assistant', content: '' })
  const aiMessageIndex = messages.value.length - 1

  try {
    // ⚠️ 注意：Axios 处理流式数据比较麻烦，这里我们用浏览器原生的 fetch！
    const response = await fetch('http://127.0.0.1:8000/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      // 把历史记录和当前问题一起发给后端
      body: JSON.stringify({ messages: messages.value.slice(0, -1) }) 
    })

    if (!response.ok) {
      throw new Error('网络请求失败')
    }

    // 🔥 见证奇迹：打开数据流通道
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 解码后端发来的二进制片段
      const chunkText = decoder.decode(value, { stream: true })
      
      // 解析像电报一样的 "data: {...}" 格式
      const lines = chunkText.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try {
            const dataObj = JSON.parse(line.substring(6))
            // 提取大模型吐出的那个字，并拼接到当前的屏幕气泡上！
            const deltaContent = dataObj.choices[0]?.delta?.content || ''
            messages.value[aiMessageIndex].content += deltaContent
            scrollToBottom() // 每打出一个字，就自动往下滚一点
          } catch (e) {
            // 解析单行失败直接忽略，防止程序崩溃
          }
        }
      }
    }
  } catch (error) {
    ElMessage.error('AI 通讯中断，请检查后端网关！')
    messages.value[aiMessageIndex].content = '【网络连接失败】'
  } finally {
    isGenerating.value = false
  }
}
</script>

<style scoped>
.storyboard-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px); /* 减去顶部导航栏和内边距的高度 */
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  overflow: hidden;
}

.chat-history {
  flex: 1;
  padding: 20px;
  background-color: #fafbfc;
}

.message-item {
  display: flex;
  margin-bottom: 20px;
  align-items: flex-start;
}

/* 我发的消息在右边 */
.message-item.user {
  flex-direction: row-reverse;
}

.avatar {
  margin: 0 15px;
  flex-shrink: 0;
}

.msg-bubble {
  max-width: 70%;
  padding: 12px 18px;
  border-radius: 8px;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
  white-space: pre-wrap; /* 保留换行符 */
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.assistant .msg-bubble {
  background: white;
  color: #333;
  border: 1px solid #ebeef5;
}

.user .msg-bubble {
  background: #ecf5ff;
  color: #409EFF;
  border: 1px solid #d9ecff;
}

.input-area {
  padding: 20px;
  background: white;
  border-top: 1px solid #ebeef5;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.hint {
  font-size: 12px;
  color: #909399;
}
</style>