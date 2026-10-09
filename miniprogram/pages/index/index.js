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
      this.setData({
        isLoggedIn: true,
        userInfo: userInfo
      })
    }
  },

  async loadAnnouncements() {
    try {
      const response = await this.request('/announcement/list', { page_size: 1 })
      if (response && response.data && response.data.list) {
        this.setData({
          announcementCount: response.data.list.length
        })
      }
    } catch (error) {
      console.error('获取公告失败:', error)
    }
  },

  async wxLogin() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const code = await app.wxLogin()

      const response = await this.request('/auth/wx-login', {
        code: code
      }, 'POST')

      if (response && response.data) {
        const { token, user } = response.data

        wx.setStorageSync('token', token)
        app.globalData.token = token
        app.globalData.userInfo = user

        this.setData({
          isLoggedIn: true,
          userInfo: user
        })

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })
      }
    } catch (error) {
      console.error('登录失败:', error)
      wx.showToast({
        title: '登录失败，请重试',
        icon: 'none'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  goToChat() {
    wx.navigateTo({
      url: '/pages/chat/chat'
    })
  },

  // 简易请求封装
  request(url, data = {}, method = 'GET') {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token')
      const baseUrl = app.globalData.baseUrl || 'http://localhost:5000/api'

      wx.request({
        url: baseUrl + url,
        data: data,
        method: method,
        header: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          if (res.data && res.data.code === 200) {
            resolve(res.data)
          } else {
            const error = new Error(res.data?.message || '请求失败')
            error.statusCode = res.statusCode
            reject(error)
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  }
})
