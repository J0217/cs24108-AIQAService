// app.js
const DEFAULT_BASE_URL = 'http://localhost:5000/api'

App({
  globalData: {
    userInfo: null,
    token: null,
    // 本地调试：真机调试请改成电脑局域网 IP（需与后端 host 0.0.0.0 一致）
    // 也可在开发者工具 Storage 中写入 baseUrl 覆盖，免改代码
    baseUrl: DEFAULT_BASE_URL,
    loginPromise: null
  },

  onLaunch() {
    // 允许通过本地存储覆盖后端地址（真机调试/多环境切换）
    const cachedBaseUrl = wx.getStorageSync('baseUrl')
    if (cachedBaseUrl) {
      this.globalData.baseUrl = cachedBaseUrl
    }
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token && userInfo) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  setBaseUrl(url) {
    const normalized = (url || '').trim().replace(/\/$/, '')
    if (!normalized) return
    this.globalData.baseUrl = normalized
    wx.setStorageSync('baseUrl', normalized)
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
            reject(new Error('微信登录失败: ' + res.errMsg))
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

  // 退出登录：清空本地登录态
  logout() {
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
    this.globalData.token = null
    this.globalData.userInfo = null
  },

  // 统一请求封装（401 自动重新登录并重试一次）
  request(path, data = {}, method = 'GET', retried = false) {
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
          const body = res.data || {}
          if (body.code === 200) {
            resolve(body)
            return
          }

          // Token 失效：清空本地登录态后自动重登，只重试一次
          const isAuthPath = path.indexOf('/auth/') === 0
          if (res.statusCode === 401 && !retried && !isAuthPath) {
            this.logout()
            this.login()
              .then(() => this.request(path, data, method, true))
              .then(resolve)
              .catch(reject)
            return
          }

          const err = new Error(body.message || '请求失败')
          err.statusCode = res.statusCode
          err.code = body.code
          reject(err)
        },
        fail: (err) => {
          const netErr = new Error('网络异常，请检查后端是否已启动')
          netErr.original = err
          reject(netErr)
        }
      })
    })
  },

  // 手动/自动登录（并发调用复用同一个 Promise，避免重复登录）
  login(force = false) {
    if (!force) {
      const token = wx.getStorageSync('token')
      if (token) return Promise.resolve(token)
      if (this.globalData.loginPromise) return this.globalData.loginPromise
    }

    const task = this.wxLogin()
      .then((code) => this.request('/auth/wx-login', { code }, 'POST'))
      .then((res) => {
        const { token: newToken, user } = res.data
        wx.setStorageSync('token', newToken)
        wx.setStorageSync('userInfo', user)
        this.globalData.token = newToken
        this.globalData.userInfo = user
        return newToken
      })
      .then((token) => {
        this.globalData.loginPromise = null
        return token
      })
      .catch((err) => {
        this.globalData.loginPromise = null
        throw err
      })

    this.globalData.loginPromise = task
    return task
  },

  // 兼容旧调用
  ensureLogin() {
    return this.login()
  }
})
