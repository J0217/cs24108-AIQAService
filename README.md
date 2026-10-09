# AI智能问答客服平台

> 基于 Flask + 微信小程序的智能客服解决方案

## 项目简介

AI智能问答客服平台是一个集 **Web后端**、**小程序** 和 **API接口** 于一体的智能客服系统。平台采用 AI/NLP 技术，根据用户问题智能匹配场景，自动生成回复内容，并提供公告推送功能。

**负责模块：E-多端接入（小程序 + API）**

### 技术栈
- **后端**: Flask + SQLAlchemy + JWT
- **小程序**: 微信小程序原生开发
- **AI服务**: OpenAI Compatible API（可切换）
- **数据库**: SQLite（开发）/ PostgreSQL（生产）

### 核心功能
1. **小程序对话界面** - 支持多场景切换、快捷回复、消息历史
2. **统一API接口** - 供外部系统调用的标准化聊天接口
3. **AI智能回复** - 根据场景自动匹配快捷模板或调用AI生成回复
4. **公告推送** - 支持多类型公告发布、阅读状态追踪

---

## 目录结构

```
AIQAService/
├── backend/                  # Flask后端
│   ├── app.py               # 应用入口
│   ├── config.py            # 配置文件
│   ├── routes/              # 路由模块
│   │   ├── auth.py          # 认证路由（登录/注册/Token）
│   │   ├── chat.py          # 对话路由（消息收发明细）
│   │   ├── announcement.py  # 公告路由（发布/推送/已读）
│   │   └── api.py           # 统一API路由（对外开放）
│   ├── services/            # 业务服务
│   │   └── ai_service.py    # AI服务（调用OpenAI/快捷回复）
│   ├── models/              # 数据模型
│   │   └── __init__.py      # 用户/对话/消息/公告/快捷回复模型
│   └── utils/               # 工具模块
│       ├── response.py      # 响应封装
│       └── validators.py    # 参数校验
├── miniprogram/             # 微信小程序
│   ├── app.js / app.json / app.wxss
│   ├── pages/
│   │   ├── index/           # 首页（登录/功能入口）
│   │   └── chat/            # 对话页（消息交互）
│   └── utils/
├── templates/               # HTML模板
├── uploads/                 # 文件上传目录
└── config/                  # 外部配置
```

---

## 快速开始

### 环境要求
- Python 3.8+
- 微信小程序开发者工具

### 后端启动

```bash
# 1. 进入项目目录
cd backend

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
export AI_API_KEY="your-openai-api-key"
export WX_APPID="your-wechat-appid"
export WX_SECRET="your-wechat-secret"

# 5. 初始化数据库
flask db upgrade

# 6. 启动服务
python app.py
# 服务运行在 http://localhost:5000
```

### 小程序配置

1. 打开微信开发者工具
2. 导入 `miniprogram` 目录
3. 修改 `app.js` 中的 `baseUrl` 指向后端地址
4. 填写真实的 `appid` 和 `secret`（在 `config.py` 中）

---

## API文档

### 基础URL
```
http://localhost:5000/api
```

### 认证方式
所有接口（除登录外）需要在请求头中携带：
```
Authorization: Bearer <token>
```

### 接口列表

#### 1. 认证接口 `/api/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/wx-login` | 微信登录 |
| POST | `/auth/login` | 账号密码登录 |
| POST | `/auth/register` | 用户注册 |
| GET | `/auth/profile` | 获取用户信息 |
| PUT | `/auth/profile` | 更新用户信息 |
| POST | `/auth/refresh` | 刷新Token |
| POST | `/auth/logout` | 退出登录 |

#### 2. 对话接口 `/api/chat`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/chat/conversations` | 获取对话列表 |
| POST | `/chat/conversations` | 创建新对话 |
| GET | `/chat/conversations/:id` | 获取对话详情 |
| DELETE | `/chat/conversations/:id` | 删除对话 |
| POST | `/chat/conversations/:id/messages` | 发送消息 |
| POST | `/chat/conversations/:id/messages/:mid/regenerate` | 重新生成回复 |
| GET | `/chat/quick-replies` | 获取快捷回复 |
| GET | `/chat/scenes` | 获取场景列表 |

#### 3. 公告接口 `/api/announcement`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/announcement/list` | 获取公告列表 |
| GET | `/announcement/list/unread` | 获取未读公告 |
| GET | `/announcement/:id` | 获取公告详情 |
| POST | `/announcement/` | 创建公告（管理员） |
| PUT | `/announcement/:id` | 更新公告（管理员） |
| DELETE | `/announcement/:id` | 删除公告（管理员） |
| POST | `/announcement/read/:id` | 标记已读 |
| GET | `/announcement/unread-count` | 获取未读数 |

#### 4. 统一API接口 `/api/v1`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/chat` | 发送消息获取AI回复 |
| GET | `/v1/quick-reply` | 获取快捷回复 |
| GET | `/v1/announcement` | 获取最新公告 |
| GET | `/v1/stats` | 获取统计数据 |

---

## AI服务说明

### 工作原理
1. **快捷回复匹配**：优先匹配预置的快捷回复模板（关键词匹配 + 场景过滤）
2. **AI生成回复**：快捷回复置信度不足时，调用AI API生成个性化回复
3. **置信度评估**：返回置信度分数，前端可据此决定是否转人工

### 场景类型
| 场景类型 | 说明 |
|---------|------|
| `general` | 通用问答 |
| `product` | 产品咨询 |
| `after_sales` | 售后服务 |
| `technical` | 技术支持 |
| `ordering` | 订单查询 |

### 配置AI服务
```python
# config.py
AI_API_KEY = "your-openai-api-key"
AI_API_BASE_URL = "https://api.openai.com/v1"
AI_MODEL = "gpt-3.5-turbo"
AI_MAX_TOKENS = 2000
AI_TEMPERATURE = 0.7
```

支持所有 OpenAI Compatible API（如 Azure OpenAI、本地部署的 LLM 等）。

---

## 数据库设计

### 核心表
- `users` - 用户表（含微信openid）
- `conversations` - 对话记录表
- `messages` - 消息表
- `announcements` - 公告表
- `user_announcements` - 用户公告阅读记录
- `quick_replies` - 快捷回复表

---

## 开发计划

- [ ] 集成更多AI模型（Claude、文心一言等）
- [ ] 增加语音识别输入
- [ ] 支持图片/文件消息
- [ ] 人工客服转接
- [ ] 多语言支持

---

## 许可证

MIT License
