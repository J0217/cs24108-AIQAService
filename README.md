# AI智能问答客服平台

> 基于 Flask + 微信小程序的智能客服解决方案

## 项目简介

AI智能问答客服平台是一个集 **Web后端**、**小程序** 和 **API接口** 于一体的智能客服系统。平台采用 AI/NLP 技术，根据用户问题智能匹配场景，自动生成回复内容，并提供公告推送功能。

**负责模块：E-多端接入（小程序 + API）**

E 模块包含两条对外通道：

- **E1 微信小程序**：`miniprogram/`，负责登录、首页公告、场景切换、消息收发与历史记录。
- **E2 开放 API**：`backend/routes/api.py`，对外提供 `/api/v1/*` 接口，使用 `X-API-Key` 鉴权。

### 技术栈
- **后端**: Flask 3.0 + Peewee ORM + PyJWT
- **小程序**: 微信小程序原生开发
- **AI服务**: OpenAI Compatible API（可切换）+ 本地场景模板匹配兜底
- **数据库**: SQLite（开发）/ PostgreSQL（生产）

### 核心功能
1. **小程序对话界面** - 支持多场景切换、动态快捷问题、消息历史、智能输入状态
2. **统一API接口** - 供外部系统调用的标准化聊天接口（X-API-Key 鉴权）
3. **AI智能回复** - 按场景 + 关键词 + 问题相似度自动匹配回复模板，未命中时调用 AI 大模型生成
4. **公告推送** - 支持多类型公告发布、生效时间控制、阅读状态追踪

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
- Python 3.8+（已在 Python 3.14 + Flask 3.0 + Peewee 4.0.3 环境验证）
- 微信小程序开发者工具

### 后端启动

```bash
# 1. 在项目根目录安装依赖
pip install -r requirements.txt

# 2. 复制并填写环境变量（可选，不填也可用本地模板模式运行）
copy .env.example .env    # Windows
# cp .env.example .env    # macOS / Linux

# 3. 启动服务（首次启动会自动建表并初始化管理员、快捷回复模板、欢迎公告）
python backend/app.py
# 也可以使用：python -m backend.app
# 服务运行在 http://localhost:5000
```

首次启动会自动创建管理员账号：`admin / admin123`（部署前请修改）。

### 小程序配置

1. 打开微信开发者工具，导入 `miniprogram` 目录
2. 修改 `app.js` 中的 `baseUrl`：本地调试可用 `http://localhost:5000/api`，
   真机调试需改成电脑局域网 IP（如 `http://192.168.x.x:5000/api`）
3. 开发工具已关闭 `urlCheck`（见 `project.config.json`），便于访问本地 HTTP 服务
4. 当前 `project.config.json` 的 `appid` 为 `touristappid`（游客模式），只适合界面预览；
   真机登录与截图需替换成自己的小程序 AppID，并在 `.env` 中填写 `WX_APPID`、`WX_SECRET`
5. 未配置 `WX_APPID`/`WX_SECRET` 时，后端使用开发态 mock openid，仍可跑通登录与对话流程

---

## API文档

### 基础URL
```
http://localhost:5000/api
```

### 认证方式

小程序与内部接口（`/api/auth`、`/api/chat`、`/api/announcement`）除公开接口外，需要在请求头中携带 JWT：

```
Authorization: Bearer <token>
```

对外开放接口（`/api/v1/*`）统一在请求头中携带 API Key：

```
X-API-Key: <key>
```

`X-API-Key` 由 `.env` 的 `API_KEYS` 配置，多个 Key 用逗号分隔；缺省值为 `demo-api-key`。缺少或无效时统一返回 HTTP 401。

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
| PUT | `/chat/conversations/:id` | 更新对话（切换场景/标题） |
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
统一API接口全部在 `api.py` 的 `before_request` 中校验 `X-API-Key`，默认开发 Key 为 `demo-api-key`（可通过 `.env` 的 `API_KEYS` 配置多个，逗号分隔）。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/chat` | 发送消息获取AI回复 |
| GET | `/v1/quick-reply` | 获取快捷回复 |
| GET | `/v1/announcement` | 获取最新公告 |
| GET | `/v1/stats` | 获取统计数据 |

调用示例：

```bash
curl -X POST http://localhost:5000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-api-key" \
  -d "{\"question\":\"如何查询订单？\",\"session_id\":\"demo-001\",\"scene_type\":\"ordering\"}"
```

返回体统一为 `{code, message, data, timestamp}`；鉴权失败返回 HTTP 401，参数缺失返回 HTTP 400。

#### 5. E 模块实现说明

| 子模块 | 关键文件 | 职责 |
|---|---|---|
| E1 小程序入口 | `miniprogram/pages/index/` | 微信登录、登录态展示、公告数量、功能入口 |
| E1 小程序对话 | `miniprogram/pages/chat/` | 场景切换、快捷问题、消息收发、历史记录、输入状态 |
| E1 请求封装 | `miniprogram/app.js` | `baseUrl` 配置、Token 注入、`ensureLogin()` 自动登录 |
| E2 开放 API | `backend/routes/api.py` | `/v1/chat`、`/v1/quick-reply`、`/v1/announcement`、`/v1/stats` |

小程序主流程：`wx.login` 获取 code → `POST /api/auth/wx-login` 换取 JWT → 首页加载公告 → 进入对话页 → 创建/复用会话 → `POST /api/chat/conversations/:id/messages` 获取 AI 回复。未配置 `WX_APPID`/`WX_SECRET` 时，后端使用开发态 mock openid，便于本地联调。

---

## 测试

E 模块的接口冒烟测试使用 Python 标准库 unittest，无需额外依赖：

```bash
python test/test_e_module.py -v
```

共 7 条用例，覆盖开放 API 鉴权（缺失/错误/正确）、`/v1/chat` 参数校验与模板命中、快捷回复/公告/统计、微信登录与场景列表、会话消息主链路。测试使用临时 SQLite 数据库，不会修改 `instance/ai_qa_service.db`。

相关文档：

- 操作手册：[docs/操作手册.md](docs/操作手册.md)
- 实验一问答册：[docs/cs24108-2024213575-金鹏宇-P08智能问答客服平台-实验一软件项目计划-问答册.md](docs/cs24108-2024213575-金鹏宇-P08智能问答客服平台-实验一软件项目计划-问答册.md)
- EA 17 与截图清单：[docs/EA17与证据截图清单.md](docs/EA17与证据截图清单.md)

---

## AI服务说明

### 工作原理
1. **场景过滤**：仅在同一场景（或通用场景）的模板中匹配
2. **相似度匹配**：结合关键词命中数与问题文本相似度（difflib）计算置信度，≥0.75 直接返回模板
3. **AI生成回复**：模板未命中且已配置真实 AI Key 时，调用大模型生成回复
4. **本地兜底**：未配置 AI Key 或调用失败时，降级为最佳模板/场景默认回复，保证服务可用
5. **置信度评估**：返回置信度分数，前端可据此决定是否转人工

### 场景类型
| 场景类型 | 说明 |
|---------|------|
| `general` | 通用问答 |
| `product` | 产品咨询 |
| `after_sales` | 售后服务 |
| `technical` | 技术支持 |
| `ordering` | 订单查询 |

### 配置AI服务
在项目根目录 `.env` 中配置：
```ini
AI_API_KEY=sk-xxxx
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-3.5-turbo
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.7
```

支持所有 OpenAI Compatible API（如 Azure OpenAI、本地部署的 LLM 等）。不配置 Key 时，系统使用数据库中的场景模板与兜底话术，仍可完整演示对话流程。

---

## 数据库设计

### 核心表
- `users` - 用户表（含微信openid、密码哈希）
- `conversations` - 对话记录表（含场景类型）
- `messages` - 消息表（含置信度、是否模板命中、响应耗时）
- `announcements` - 公告表
- `user_announcements` - 用户公告阅读记录
- `quick_replies` - 快捷回复/场景模板表

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
