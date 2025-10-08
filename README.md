# 新闻聚合引擎 (AutoTopicSum)

一个基于 Vue + Flask 的新闻聚合引擎，支持从多个数据源搜索和聚合新闻内容。

## 技术栈

### 后端
- **Flask** - Python Web框架
- **BeautifulSoup4** - HTML解析
- **Feedparser** - RSS Feed解析
- **Requests** - HTTP请求库

### 前端
- **Vue 3** - 前端框架
- **Vite** - 构建工具
- **shadcn/ui (Radix Vue)** - UI组件库
- **Tailwind CSS** - CSS框架
- **Axios** - HTTP客户端

## 项目结构

```
AutoTopicSum/
├── backend/                      # 后端服务
│   ├── app/
│   │   ├── core/                # 核心模块
│   │   │   ├── base_source.py   # 数据源基类
│   │   │   └── aggregator.py    # 聚合器
│   │   ├── sources/             # 数据源实现
│   │   │   └── google_news.py   # Google News爬虫
│   │   ├── services/            # 业务服务
│   │   │   └── event_service.py # 事件服务
│   │   └── routes/              # API路由
│   │       └── events.py        # 事件接口
│   ├── config.py                # 配置文件
│   ├── run.py                   # 启动入口
│   └── requirements.txt         # Python依赖
│
└── frontend/                     # 前端应用
    ├── src/
    │   ├── api/                 # API封装
    │   ├── components/          # UI组件
    │   ├── views/               # 页面视图
    │   └── router/              # 路由配置
    └── package.json             # Node.js依赖
```

## 核心功能

### 1. 多数据源聚合框架
- **抽象基类 (BaseNewsSource)**: 定义统一的数据源接口
- **聚合器 (NewsAggregator)**: 并发调用多个数据源并合并结果
- **扩展性**: 可轻松添加新的数据源（继承BaseNewsSource即可）

### 2. Google News爬虫
- 基于RSS Feed进行数据获取
- 支持关键词搜索
- 支持语言和地区配置
- 自动解析标题、摘要、发布时间等信息

### 3. API接口
- `GET /api/events/search?query=关键词` - 搜索并聚合新闻
- `GET /api/events` - 获取所有事件列表
- `GET /api/events/<id>` - 获取事件详情
- `GET /api/health` - 健康检查

## 快速开始

### 后端启动

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
cp .env.example .env

# 启动服务
python run.py
```

后端将运行在 http://localhost:5001

或使用启动脚本（macOS/Linux）：
```bash
cd backend
chmod +x start.sh
./start.sh
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将运行在 http://localhost:3000

或使用启动脚本（macOS/Linux）：
```bash
cd frontend
chmod +x start.sh
./start.sh
```

## 使用示例

### 1. 搜索新闻

在前端搜索框输入关键词（例如："人工智能"），系统将：
1. 并发调用所有已注册的数据源（当前为Google News）
2. 聚合所有返回的新闻文章
3. 去重并按时间排序
4. 生成事件摘要并展示

### 2. API调用示例

```bash
# 搜索关键词 "人工智能"
curl "http://localhost:5001/api/events/search?query=人工智能&language=zh-CN&region=CN"

# 获取所有事件
curl "http://localhost:5001/api/events"

# 获取特定事件详情
curl "http://localhost:5001/api/events/abc123def456"
```

## 扩展数据源

要添加新的数据源，只需：

1. 在 `backend/app/sources/` 创建新文件
2. 继承 `BaseNewsSource` 类
3. 实现 `search()` 和 `get_latest()` 方法
4. 在 `event_service.py` 中注册新数据源

示例：

```python
from app.core.base_source import BaseNewsSource, NewsArticle

class MyNewsSource(BaseNewsSource):
    def __init__(self):
        super().__init__("My News Source")
    
    def search(self, query: str, **kwargs) -> List[NewsArticle]:
        # 实现搜索逻辑
        pass
    
    def get_latest(self, limit: int = 10) -> List[NewsArticle]:
        # 实现获取最新新闻逻辑
        pass

# 在 event_service.py 中注册
my_source = MyNewsSource()
aggregator.register_source(my_source)
```

## 架构特点

### 后端架构
- **分层设计**: Core(核心) → Sources(数据源) → Services(服务) → Routes(路由)
- **并发处理**: 使用 ThreadPoolExecutor 并发调用多个数据源
- **错误隔离**: 单个数据源失败不影响其他数据源
- **模块化**: 每个模块职责单一，便于维护和扩展

### 前端架构
- **组件化**: 基于 shadcn/ui 的可复用组件
- **响应式设计**: 适配移动端和桌面端
- **API封装**: 统一的 HTTP 客户端和错误处理

## 注意事项

1. **数据存储**: 当前使用内存缓存，生产环境建议使用数据库
2. **速率限制**: Google News有速率限制，频繁请求可能被限制
3. **错误处理**: 已实现基本错误处理，建议添加更完善的日志和监控
4. **性能优化**: 可添加Redis缓存以提升响应速度

## 依赖说明

### 后端核心依赖
- `Flask==3.0.0` - Web框架
- `requests==2.31.0` - HTTP请求
- `beautifulsoup4==4.12.2` - HTML解析
- `feedparser==6.0.10` - RSS解析

### 前端核心依赖
- `vue@^3.4.0` - 前端框架
- `radix-vue@^1.2.0` - UI组件
- `axios@^1.6.0` - HTTP客户端
- `tailwindcss@^3.4.0` - CSS框架

