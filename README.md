# Cloudflare IP优选系统

> 基于 [cmliu/edgetunnel](https://github.com/cmliu/edgetunnel) 项目开发的IP优选管理系统

## 📄 许可证

本项目基于 GNU General Public License v2.0 许可证开源。

- 原项目: [cmliu/edgetunnel](https://github.com/cmliu/edgetunnel)
- Fork项目: [RATING3PRO/edgetunnel](https://github.com/RATING3PRO/edgetunnel)
- 许可证: GPL v2.0
- 本项目遵循相同的开源许可证要求

### 重要说明

本项目是基于原开源项目的扩展开发，主要添加了：
- KV空间管理API
- Python客户端IP优选功能
- 系统测试工具

所有新增代码同样遵循 GPL v2.0 许可证。

这是一个基于Cloudflare Workers的IP优选系统，包含KV管理API和本地Python客户端，可以实时根据本地网络环境优选IP并自动更新到KV空间。

## 项目结构

```
CFKVIPUPDATE/
├── .github/
│   └── workflows/         # GitHub Actions工作流
├── _worker.js              # 原有的Cloudflare Workers项目
├── kv-manager-worker.js    # 新的KV管理API Workers项目
├── ip_optimizer.py         # Python IP优选客户端（命令行版）
├── ip_optimizer_gui.py     # Python IP优选客户端（GUI版）
├── test_system.py          # 系统功能测试工具
├── config.json            # 配置文件
├── requirements.txt       # Python依赖
├── wrangler.toml          # Wrangler配置
├── LICENSE               # GPL v2.0 许可证
├── .gitignore            # Git忽略文件
└── README.md             # 说明文档
```

## 功能特性

### KV管理API (kv-manager-worker.js)
-  RESTful API接口，支持读取和写入KV空间
-  完整的CORS支持，可从任何域名访问
-  提供健康检查和统计信息接口
-  自动去重和内容大小检查
-  支持追加和替换两种更新模式
-  Web管理界面

### Python客户端
- **命令行版本** (`ip_optimizer.py`)：适合自动化脚本和服务器环境
- **GUI版本** (`ip_optimizer_gui.py`)：提供图形界面，操作更直观
-  高并发IP延迟测试
-  支持多种IP来源（官方、CM整理、AS列表等）
-  灵活的配置选项
-  实时进度显示和详细日志
-  自动上传最优IP到KV空间
-  支持追加和替换模式

### 系统测试工具
- **测试工具** (`test_system.py`)：全面的系统功能验证工具
-  API健康检查和Web界面访问测试
-  KV存储的读取、写入和统计功能测试
-  IP优选流程完整性模拟测试
-  自动化测试报告和结果统计
-  支持自定义配置和命令行参数

## 部署指南

### 1. 部署KV管理API

#### 步骤1：创建KV命名空间
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 `Workers & Pages` → `KV`
3. 创建一个新的KV命名空间，例如命名为 `IP_OPTIMIZER`

#### 步骤2：部署Workers
1. 进入 `Workers & Pages` → `Create application` → `Create Worker`
2. 将 `kv-manager-worker.js` 的内容复制到编辑器中
3. 点击 `Save and Deploy`

#### 步骤3：绑定KV命名空间
1. 在Worker设置页面，进入 `Settings` → `Variables`
2. 在 `KV Namespace Bindings` 部分点击 `Add binding`
3. 设置：
   - Variable name: `KV`
   - KV namespace: 选择刚创建的命名空间
4. 点击 `Save and deploy`

#### 步骤4：设置环境变量（鉴权配置）
1. 在Worker设置页面，进入 `Settings` → `Variables`
2. 在 `Environment Variables` 部分点击 `Add variable`
3. 设置：
   - Variable name: `API_KEY`
   - Value: 设置一个强密码作为API访问密钥（例如：`your_secure_api_key_123`）
4. 点击 `Save and deploy`

#### 步骤5：获取API URL
部署完成后，你会得到一个类似这样的URL：
```
https://your-worker.your-subdomain.workers.dev
```

### 2. 配置Python客户端

#### 步骤1：安装Python依赖
```bash
pip install -r requirements.txt
```

#### 步骤2：配置文件设置
编辑 `config.json` 文件，填入你的配置信息：
```json
{
  "timeout": 3,
  "max_workers": 50,
  "test_count": 3,
  "best_count": 16,
  "default_ip_source": "official",
  "default_port": 443,
  "default_action": "replace",
  "worker_url": "https://your-worker.your-subdomain.workers.dev",
  "worker_api_key": "YOUR_WORKER_API_KEY_HERE"
}
```

**配置项说明：**
- `worker_url`: 部署Worker后获得的URL
- `worker_api_key`: 在Worker环境变量中设置的API_KEY值

## 使用方法

### 命令行版本

```bash
# 使用默认配置运行优选
python ip_optimizer.py

# 指定IP来源和端口
python ip_optimizer.py --source cm --port 8443

# 追加模式（不覆盖现有IP）
python ip_optimizer.py --action append

# 使用自定义配置文件
python ip_optimizer.py --config my_config.json
```

### GUI版本

```bash
# 启动图形界面版本
python ip_optimizer_gui.py
```

GUI版本功能：
- 直观的图形界面操作
- 实时显示优选进度
- 可视化配置参数设置
- 结果展示和导出功能
- 日志信息实时查看

### 系统测试

```bash
# 运行完整的系统功能测试
python test_system.py

# 使用自定义配置文件
python test_system.py --config my_config.json

# 指定API URL（覆盖配置文件设置）
python test_system.py --api-url https://your-worker.workers.dev
```

**测试项目包括：**
- API健康检查
- Web界面访问测试
- IP列表获取功能
- IP列表更新功能
- 统计信息接口
- IP优选流程模拟

测试工具会自动运行所有测试项目并生成详细报告，帮助验证系统各项功能是否正常工作。

### 命令行参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `--config` | 配置文件路径 | 默认: config.json |
| `--api-url` | Workers API URL | 覆盖配置文件中的设置 |
| `--source` | IP来源 | official, cm, as13335, as209242, proxyip |
| `--port` | 测试端口 | 443, 2053, 2083, 2087, 2096, 8443 |
| `--action` | 操作类型 | replace（替换）, append（追加） |
| `--create-config` | 创建默认配置文件 | - |

### IP来源说明

- **official**: Cloudflare官方IP段
- **cm**: CM整理的优质IP列表
- **as13335**: Cloudflare AS13335 IP段
- **as209242**: Cloudflare AS209242 IP段
- **proxyip**: 反代IP列表（直接可用IP）

### 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `api_url` | Workers API地址 | 必填 |
| `timeout` | 单次连接超时时间（秒） | 3 |
| `max_workers` | 最大并发测试数 | 50 |
| `test_count` | 每个IP测试次数 | 3 |
| `best_count` | 保存的最优IP数量 | 16 |
| `default_ip_source` | 默认IP来源 | official |
| `default_port` | 默认测试端口 | 443 |
| `default_action` | 默认操作类型 | replace |
| `worker_url` | Worker API地址 | 必填 |
| `worker_api_key` | Worker API密钥 | 必填 |

## API接口文档

### 鉴权说明

所有API接口（除首页和健康检查外）都需要提供API密钥进行鉴权。支持以下三种方式：

1. **请求头方式**（推荐）：
```http
X-API-Key: your_api_key_here
```

2. **Authorization头方式**：
```http
Authorization: Bearer your_api_key_here
```

3. **URL参数方式**：
```http
GET /api/ips?api_key=your_api_key_here
```

### 获取IP列表
```http
GET /api/ips?key=ADD.txt&format=json
X-API-Key: your_api_key_here
```

**参数：**
- `key` (可选): KV键名，默认为 'ADD.txt'
- `format` (可选): 返回格式 'json' 或 'text'，默认为 'json'

**响应：**
```json
{
  "success": true,
  "data": {
    "key": "ADD.txt",
    "count": 16,
    "ips": ["1.1.1.1:443", "8.8.8.8:443"],
    "lastUpdated": "2024-01-01T00:00:00.000Z"
  }
}
```

### 更新IP列表
```http
POST /api/ips
Content-Type: application/json
X-API-Key: your_api_key_here

{
  "ips": ["1.1.1.1:443", "8.8.8.8:443"],
  "action": "replace",
  "key": "ADD.txt"
}
```

**参数：**
- `ips`: IP列表数组
- `action`: 操作类型，'replace'（替换）或 'append'（追加）
- `key`: KV键名，可选

### 健康检查
```http
GET /api/health
```

### 统计信息
```http
GET /api/stats
```

## 自动化部署

### 定时任务
可以使用系统的定时任务功能定期运行IP优选：

**Windows (任务计划程序):**
1. 打开任务计划程序
2. 创建基本任务
3. 设置触发器（如每小时运行一次）
4. 操作设置为运行程序：`python`
5. 参数设置为：`C:\path\to\ip_optimizer.py`

**Linux (crontab):**
```bash
# 每小时运行一次
0 * * * * cd /path/to/project && python3 ip_optimizer.py

# 每天凌晨2点运行
0 2 * * * cd /path/to/project && python3 ip_optimizer.py --source cm --port 8443
```

### Docker部署
创建 `Dockerfile`：
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "ip_optimizer.py"]
```

构建和运行：
```bash
docker build -t ip-optimizer .
docker run -v $(pwd)/config.json:/app/config.json ip-optimizer
```

## 故障排除

### 常见问题

**1. API连接失败**
- 检查Workers URL是否正确
- 确认KV命名空间已正确绑定
- 检查网络连接

**2. 测试结果全部为-1**
- 可能是网络运营商阻断，尝试更换端口
- 检查防火墙设置
- 尝试不同的IP来源

**3. 上传失败**
- 检查KV空间配额
- 确认API URL正确
- 查看详细错误日志

### 日志文件
程序运行时会生成 `ip_optimizer.log` 日志文件，包含详细的运行信息和错误信息。

## 注意事项

1. **网络环境**: 建议在直连网络环境下运行，避免代理影响测试结果
2. **并发限制**: 根据网络环境调整 `max_workers` 参数，避免过高并发
3. **KV配额**: Cloudflare KV有读写次数限制，注意使用频率
4. **IP来源**: 不同来源的IP质量可能不同，建议测试后选择最适合的来源
5. **API密钥安全**: 
   - 请妥善保管Worker API密钥，不要在代码中硬编码
   - 建议定期更换API密钥
   - 将 `config.json` 添加到 `.gitignore` 文件中，避免泄露配置信息
   - 使用强密码作为API密钥，建议包含字母、数字和特殊字符

## 许可证

本项目基于现有的Cloudflare Workers项目扩展，遵循相同的使用条款。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 实现KV管理API
- 实现Python IP优选客户端
- 支持多种IP来源和端口
- 完整的文档和配置
