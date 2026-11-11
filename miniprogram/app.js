// app.js
App({
  globalData: {
    userInfo: null,
    token: null,
    // 本地调试：真机调试请改成电脑局域网 IP（需与后端 host 0.0.0.0 一致）
    baseUrl: 'http://localhost:5000/api'
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token && userInfo) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  // 微信登录，返回 code
  wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          if (res.code) {
            this.globalData.wxCode = res.code
            resolve(res.code)
          } else {
            reject(new Error('登录失败: ' + res.errMsg))
          }
        },
        fail: reject
      })
    })
  },

  // 获取用户信息（可选，用于完善资料）
  getUserInfo() {
    return new Promise((resolve, reject) => {
      wx.getUserProfile({
        desc: '用于完善用户资料',
        success: (res) => {
          this.globalData.userInfo = res.userInfo
          wx.setStorageSync('userInfo', res.userInfo)
          resolve(res.userInfo)
        },
        fail: reject
      })
    })
  },

  // 统一请求封装
  request(path, data = {}, method = 'GET') {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token')
      wx.request({
        url: this.globalData.baseUrl + path,
        data,
        method,
        header: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          if (res.data && res.data.code === 200) {
            resolve(res.data)
          } else {
            const err = new Error((res.data && res.data.message) || '请求失败')
            err.statusCode = res.statusCode
            err.code = res.data && res.data.code
            reject(err)
          }
        },
        fail: reject
      })
    })
  },

  // 确保已登录，未登录则自动微信登录
  ensureLogin() {
    const token = wx.getStorageSync('token')
    if (token) {
      return Promise.resolve(token)
    }
    return this.wxLogin()
      .then((code) => this.request('/auth/wx-login', { code }, 'POST'))
      .then((res) => {
        const { token: newToken, user } = res.data
        wx.setStorageSync('token', newToken)
        wx.setStorageSync('userInfo', user)
        this.globalData.token = newToken
        this.globalData.userInfo = user
        return newToken
      })
  }
})
