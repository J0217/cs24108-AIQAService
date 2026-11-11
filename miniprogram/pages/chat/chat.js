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
    showHistory: false,
    showHelp: false,
    scenes: [],
    conversations: [],
    currentScene: 'general',
    currentSceneName: '通用问答',
    conversationId: null,
    scrollToView: '',
    userInfo: {},
    quickQuestions: [],
    failedContent: ''
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
        const questions = (res.data || []).map((item) => item.question).slice(0, 6)
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
        return this.createConversation(this.data.currentScene)
      })
      .then(() => this.loadQuickReplies())
  },

  createConversation(scene) {
    return app.request('/chat/conversations', {
      title: '新对话',
      scene_type: scene || this.data.currentScene,
      reuse_empty: true
    }, 'POST').then((res) => {
      this.setData({
        conversationId: res.data.id,
        messages: [],
        scrollToView: ''
      })
      return res.data.id
    })
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
    return scene ? scene.name : (SCENE_NAMES[type] || type)
  },

  formatMessage(message) {
    return {
      ...message,
      confidencePercent: message.confidence ? Math.round(message.confidence * 100) : null
    }
  },

  // ==================== 历史会话 ====================
  toggleHistory() {
    const next = !this.data.showHistory
    this.setData({ showHistory: next })
    if (next) this.loadConversations()
  },

  loadConversations() {
    app.request('/chat/conversations?page_size=30')
      .then((res) => {
        const list = (res.data.list || []).map((c) => ({
          ...c,
          sceneIcon: SCENE_ICONS[c.scene_type] || '💬',
          sceneName: SCENE_NAMES[c.scene_type] || c.scene_type,
          active: c.id === this.data.conversationId
        }))
        this.setData({ conversations: list })
      })
      .catch((err) => console.error('获取历史会话失败:', err))
  },

  selectConversation(e) {
    const { id } = e.currentTarget.dataset
    if (!id) return
    const target = this.data.conversations.find((c) => c.id === id)
    this.setData({
      showHistory: false,
      conversationId: id,
      currentScene: target ? target.scene_type : this.data.currentScene,
      currentSceneName: target ? target.sceneName : this.data.currentSceneName
    })
    this.loadMessages(id)
    this.loadQuickReplies()
  },

  startNewConversation() {
    this.setData({ showHistory: false })
    this.createConversation(this.data.currentScene)
      .then(() => this.loadQuickReplies())
      .catch((err) => wx.showToast({ title: err.message || '创建失败', icon: 'none' }))
  },

  deleteConversation(e) {
    const { id } = e.currentTarget.dataset
    wx.showModal({
      title: '删除会话',
      content: '删除后该会话将不再显示，确定继续？',
      success: (res) => {
        if (!res.confirm) return
        app.request('/chat/conversations/' + id, {}, 'DELETE')
          .then(() => {
            const remain = this.data.conversations.filter((c) => c.id !== id)
            this.setData({ conversations: remain })
            if (id === this.data.conversationId) {
              this.setData({ conversationId: null, messages: [] })
              return this.createConversation(this.data.currentScene)
            }
          })
          .catch((err) => wx.showToast({ title: err.message || '删除失败', icon: 'none' }))
      }
    })
  },

  // ==================== 帮助 ====================
  toggleHelp() {
    this.setData({ showHelp: !this.data.showHelp })
  },

  copyServicePhone() {
    wx.setClipboardData({
      data: '400-800-1234',
      success: () => wx.showToast({ title: '客服电话已复制', icon: 'none' })
    })
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

  // 发送失败后点击重试
  retrySend() {
    const content = this.data.failedContent
    if (!content) return
    this.setData({ failedContent: '' })
    this.sendText(content, true)
  },

  sendText(rawContent, skipFailedClear) {
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
    if (skipFailedClear) this.setData({ failedContent: '' })
    this.scrollToBottom('msg-' + tempId)

    const conversationId = this.data.conversationId
    const sendRequest = conversationId
      ? this.postMessage(conversationId, content)
      : this.createConversation(this.data.currentScene).then((id) => this.postMessage(id, content))

    sendRequest.then((res) => {
      const { user_message, assistant_message } = res.data
      const messages = this.data.messages.filter((m) => m.id !== tempId)
      messages.push(this.formatMessage(user_message), this.formatMessage(assistant_message))
      this.setData({ messages, isSending: false, typing: false, failedContent: '' })
      this.scrollToBottom('msg-' + assistant_message.id)
    }).catch((err) => {
      console.error('发送消息失败:', err)
      this.setData({
        isSending: false,
        typing: false,
        failedContent: content,
        canSend: false
      })
      wx.showToast({ title: err.message || '发送失败，可点击消息重试', icon: 'none' })
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

  // 切换场景时新建会话，避免改写历史会话的场景归属
  switchScene(scene) {
    if (!scene || scene === this.data.currentScene) return Promise.resolve()
    this.setData({
      currentScene: scene,
      currentSceneName: this.findSceneName(scene)
    })

    return this.createConversation(scene)
      .then(() => this.loadQuickReplies())
      .then(() => {
        wx.showToast({ title: '已切换到' + this.findSceneName(scene), icon: 'none' })
      })
      .catch((err) => console.error('切换场景失败:', err))
  },

  onShareAppMessage() {
    return {
      title: 'AI智能客服 · 7×24小时在线解答',
      path: '/pages/index/index'
    }
  }
})
