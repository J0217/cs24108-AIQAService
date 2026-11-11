// pages/chat/chat.js
const app = getApp()

const SCENE_ICONS = {
  general: '💬',
  product: '🛍️',
  after_sales: '🎧',
  technical: '🔧',
  ordering: '📦'
}

const SCENE_NAMES = {
  general: '通用问答',
  product: '产品咨询',
  after_sales: '售后服务',
  technical: '技术支持',
  ordering: '订单查询'
}

Page({
  data: {
    messages: [],
    inputValue: '',
    canSend: false,
    isSending: false,
    typing: false,
    showScenePicker: false,
    scenes: [],
    currentScene: 'general',
    currentSceneName: '通用问答',
    conversationId: null,
    scrollToView: '',
    userInfo: {},
    quickQuestions: []
  },

  onLoad(options) {
    const entryScene = options && options.scene ? decodeURIComponent(options.scene) : ''
    this.setData({
      userInfo: wx.getStorageSync('userInfo') || {},
      currentScene: entryScene || this.data.currentScene,
      currentSceneName: entryScene ? (SCENE_NAMES[entryScene] || entryScene) : this.data.currentSceneName
    })
    this.loadScenes()

    app.ensureLogin()
      .then(() => this.initConversation())
      .then(() => {
        if (options && options.question) {
          this.sendText(decodeURIComponent(options.question))
        }
      })
      .catch((err) => {
        console.error('初始化对话失败:', err)
        wx.showToast({ title: err.message || '服务连接失败', icon: 'none' })
      })
  },

  // ==================== 初始化数据 ====================
  loadScenes() {
    app.request('/chat/scenes').then((res) => {
      const scenes = (res.data || []).map((item) => ({
        ...item,
        icon: SCENE_ICONS[item.type] || '💬'
      }))
      const current = scenes.find((s) => s.type === this.data.currentScene)
      this.setData({
        scenes,
        currentSceneName: current ? current.name : this.data.currentSceneName
      })
    }).catch((err) => console.error('获取场景失败:', err))
  },

  loadQuickReplies() {
    return app.request('/chat/quick-replies?scene_type=' + this.data.currentScene)
      .then((res) => {
        const questions = (res.data || []).map((item) => item.question)
        this.setData({ quickQuestions: questions })
      })
      .catch((err) => console.error('获取快捷问题失败:', err))
  },

  initConversation() {
    return app.request('/chat/conversations?scene_type=' + this.data.currentScene)
      .then((res) => {
        const list = res.data.list || []
        if (list.length > 0) {
          this.setData({
            conversationId: list[0].id,
            currentScene: list[0].scene_type,
            currentSceneName: this.findSceneName(list[0].scene_type)
          })
          return this.loadMessages(list[0].id)
        }
        return app.request('/chat/conversations', {
          title: '新对话',
          scene_type: this.data.currentScene
        }, 'POST').then((createRes) => {
          this.setData({ conversationId: createRes.data.id })
        })
      })
      .then(() => this.loadQuickReplies())
  },

  loadMessages(conversationId) {
    return app.request('/chat/conversations/' + conversationId)
      .then((res) => {
        const messages = (res.data.messages || []).map((m) => this.formatMessage(m))
        this.setData({ messages })
        this.scrollToBottom(messages.length ? 'msg-' + messages[messages.length - 1].id : '')
      })
  },

  findSceneName(type) {
    const scene = this.data.scenes.find((s) => s.type === type)
    return scene ? scene.name : type
  },

  formatMessage(message) {
    return {
      ...message,
      confidencePercent: message.confidence ? Math.round(message.confidence * 100) : null
    }
  },

  // ==================== 消息发送 ====================
  handleInput(e) {
    const inputValue = e.detail.value
    this.setData({
      inputValue,
      canSend: !!inputValue.trim() && !this.data.isSending
    })
  },

  handleConfirm() {
    this.handleSend()
  },

  handleSend() {
    this.sendText(this.data.inputValue)
  },

  handleQuickQuestion(e) {
    const question = e.currentTarget.dataset.question
    this.sendText(question)
  },

  sendText(rawContent) {
    const content = (rawContent || '').trim()
    if (!content || this.data.isSending) return

    const tempId = 'temp-' + Date.now()
    const tempMessage = { id: tempId, role: 'user', content, confidencePercent: null }
    this.setData({
      messages: this.data.messages.concat(tempMessage),
      inputValue: '',
      canSend: false,
      isSending: true,
      typing: true
    })
    this.scrollToBottom('msg-' + tempId)

    const conversationId = this.data.conversationId
    const sendRequest = conversationId
      ? this.postMessage(conversationId, content)
      : app.request('/chat/conversations', {
        title: content.slice(0, 30),
        scene_type: this.data.currentScene
      }, 'POST').then((createRes) => {
        this.setData({ conversationId: createRes.data.id })
        return this.postMessage(createRes.data.id, content)
      })

    sendRequest.then((res) => {
      const { user_message, assistant_message } = res.data
      const messages = this.data.messages.filter((m) => m.id !== tempId)
      messages.push(this.formatMessage(user_message), this.formatMessage(assistant_message))
      this.setData({ messages, isSending: false, typing: false })
      this.scrollToBottom('msg-' + assistant_message.id)
    }).catch((err) => {
      console.error('发送消息失败:', err)
      this.setData({ isSending: false, typing: false })
      wx.showToast({ title: err.message || '发送失败，请重试', icon: 'none' })
    })
  },

  postMessage(conversationId, content) {
    return app.request(`/chat/conversations/${conversationId}/messages`, { content }, 'POST')
  },

  scrollToBottom(viewId) {
    if (!viewId) return
    wx.nextTick(() => this.setData({ scrollToView: viewId }))
  },

  // ==================== 场景切换 ====================
  toggleScenePicker() {
    this.setData({ showScenePicker: !this.data.showScenePicker })
  },

  handleSceneChange(e) {
    const scene = e.currentTarget.dataset.scene
    this.setData({ showScenePicker: false })
    this.switchScene(scene)
  },

  switchScene(scene) {
    if (!scene || scene === this.data.currentScene) return Promise.resolve()
    this.setData({
      currentScene: scene,
      currentSceneName: this.findSceneName(scene)
    })

    const updateRequest = this.data.conversationId
      ? app.request(`/chat/conversations/${this.data.conversationId}`, { scene_type: scene }, 'PUT')
      : Promise.resolve()

    return updateRequest
      .then(() => this.loadQuickReplies())
      .then(() => {
        wx.showToast({ title: '已切换到' + this.findSceneName(scene), icon: 'none' })
      })
      .catch((err) => console.error('切换场景失败:', err))
  }
})
