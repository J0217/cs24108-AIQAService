// pages/index/index.js
const app = getApp()

Page({
  data: {
    isLoggedIn: false,
    userInfo: null,
    announcementCount: 0,
    loading: false
  },

  onLoad() {
    this.checkLoginStatus()
    this.loadAnnouncements()
  },

  onShow() {
    this.checkLoginStatus()
    this.loadAnnouncements()
  },

  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token && userInfo) {
      this.setData({ isLoggedIn: true, userInfo })
    }
  },

  loadAnnouncements() {
    const token = wx.getStorageSync('token')
    // 已登录优先用未读数接口（更准确），未登录退回公开列表
    const request = token
      ? app.request('/announcement/unread-count')
          .then((res) => ({ count: (res.data && res.data.unread_count) || 0 }))
          .catch(() => ({ count: 0 }))
      : Promise.resolve({ count: 0 })

    request.then(({ count }) => {
      if (count > 0) {
        this.setData({ announcementCount: count })
        return
      }
      app.request('/announcement/list', { page_size: 20 })
        .then((response) => {
          const list = (response.data && response.data.list) || []
          this.setData({ announcementCount: list.length })
        })
        .catch((error) => console.error('获取公告失败:', error))
    })
  },

  wxLogin() {
    if (this.data.loading) return

    this.setData({ loading: true })
    app.ensureLogin()
      .then(() => {
        const userInfo = wx.getStorageSync('userInfo') || {}
        this.setData({ isLoggedIn: true, userInfo })
        wx.showToast({ title: '登录成功', icon: 'success' })
      })
      .catch((error) => {
        console.error('登录失败:', error)
        wx.showToast({ title: '登录失败，请重试', icon: 'none' })
      })
      .then(() => this.setData({ loading: false }))
  },

  // 进入对话页，支持携带场景与指定问题
  goToChat(e) {
    const dataset = (e && e.currentTarget && e.currentTarget.dataset) || {}
    const params = []
    if (dataset.scene) {
      params.push('scene=' + encodeURIComponent(dataset.scene))
    }
    if (dataset.question) {
      params.push('question=' + encodeURIComponent(dataset.question))
    }
    const url = '/pages/chat/chat' + (params.length ? '?' + params.join('&') : '')
    wx.navigateTo({ url })
  },

  // 进入公告中心
  goToAnnouncement() {
    wx.navigateTo({ url: '/pages/announcement/announcement' })
  }
})
