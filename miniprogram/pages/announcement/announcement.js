// pages/announcement/announcement.js
const app = getApp()

const TYPE_LABELS = {
  notice: '通知',
  promotion: '活动',
  system: '系统'
}

Page({
  data: {
    announcements: [],
    loading: true,
    unreadCount: 0,
    expandedId: null
  },

  onLoad() {
    app.ensureLogin()
      .then(() => this.loadAnnouncements())
      .catch(() => this.loadAnnouncements())
  },

  onPullDownRefresh() {
    this.loadAnnouncements().then(() => wx.stopPullDownRefresh())
  },

  loadAnnouncements() {
    this.setData({ loading: true })
    return app.request('/announcement/list?page_size=20')
      .then((res) => {
        const list = (res.data.list || []).map((item) => ({
          ...item,
          typeLabel: TYPE_LABELS[item.type] || '公告',
          dateText: this.formatDate(item.created_at)
        }))
        this.setData({ announcements: list, loading: false })
        return this.loadUnreadCount()
      })
      .catch((err) => {
        console.error('加载公告失败:', err)
        this.setData({ loading: false })
        wx.showToast({ title: err.message || '加载失败', icon: 'none' })
      })
  },

  loadUnreadCount() {
    return app.request('/announcement/unread-count')
      .then((res) => this.setData({ unreadCount: (res.data && res.data.unread_count) || 0 }))
      .catch(() => {})
  },

  formatDate(iso) {
    if (!iso) return ''
    return iso.replace('T', ' ').slice(0, 16)
  },

  toggleDetail(e) {
    const { id } = e.currentTarget.dataset
    const isOpen = this.data.expandedId === id
    this.setData({ expandedId: isOpen ? null : id })
    if (!isOpen) this.markRead(id)
  },

  markRead(id) {
    app.request('/announcement/read/' + id, {}, 'POST')
      .then(() => {
        const announcements = this.data.announcements.map((item) => (
          item.id === id ? { ...item, is_read: 1 } : item
        ))
        this.setData({
          announcements,
          unreadCount: Math.max(0, this.data.unreadCount - 1)
        })
      })
      .catch((err) => console.error('标记已读失败:', err))
  }
})
