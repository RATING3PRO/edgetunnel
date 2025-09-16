# Cloudflare IP优选系统

> 基于 [cmliu/edgetunnel](https://github.com/cmliu/edgetunnel) 项目开发的IP优选管理系统

## 许可证

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
│   └── workflows/         # 原有的GitHub Actions工作流
├── _worker.js              # 原有的Cloudflare Workers项目
├── kv-manager-worker.js    # 新的KV管理API Workers项目
├── ip_optimizer.py         # Python IP优选客户端（命令行版）
├── ip_optimizer_gui.py     # Python IP优选客户端（GUI版）
├── ip_optimizer_standalone.py  # Python IP优选客户端（独立版源码）
├── test_system.py          # 系统功能测试工具
├── config.json            # 配置文件
├── requirements.txt       # Python依赖
├── requirements_standalone.txt  # 独立版本依赖
├── build_standalone.py     # 独立版本打包脚本
├── dist/
│   └── CloudflareIPOptimizer.exe  # 独立版本可执行文件
├── wrangler.toml          # 原有的Wrangler配置
├── LICENSE               # 使用原项目相同的GPL v2.0 许可证
├── .gitignore            # Git忽略文件
├── 独立版本使用说明.md      # 独立版本详细使用说明
└── README.md             # 新的说明文档
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
- **独立版本** (`CloudflareIPOptimizer.exe`)：单文件可执行程序，无需Python环境
  - 内置GUI界面，操作简便
  - 单个exe文件（约9.5MB），开箱即用
  - 内置配置管理，无需外部配置文件
  - 支持所有核心功能：多IP源、多端口测试、追加/替换模式
  - 实时日志显示和进度跟踪
  - 适合普通用户和无Python环境的系统
-  高并发IP延迟测试
-  支持多种IP来源（官方、CM整理、AS列表等）
-  **自定义IP数量限制**：支持用户自定义获取的IP数量，提高测试效率
-  灵活的配置选项
-  实时进度显示和详细日志
-  自动上传最优IP到KV空间
-  支持追加和替换模式
-  **新格式支持**：IP上传格式已更新为 `ip:port#延迟ms`，便于了解每个IP的性能表现

### 系统测试工具
- **测试工具** (`test_system.py`)：全面的系统功能验证工具
-  API健康检查和Web界面访问测试
-  KV存储的读取、写入和统计功能测试
-  IP优选流程完整性模拟测试
-  自动化测试报告和结果统计
-  支持自定义配置和命令行参数

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置设置

首次使用需要创建配置文件：

```bash
# 复制示例配置文件
cp config.example.json config.json

# 或在Windows中
copy config.example.json config.json
```

然后编辑 `config.json` 文件，填入您的Worker信息：

```json
{
  "worker_url": "https://your-worker.your-subdomain.workers.dev",
  "worker_api_key": "your-api-key-here",
  "timeout": 3,
  "max_workers": 50,
  "test_count": 3,
  "best_count": 16,
  "ip_count": 0,
  "default_ip_source": "official",
  "default_port": 443,
  "default_action": "replace"
}```

**重要说明：**
- `worker_url`：您的Cloudflare Worker部署地址
- `worker_api_key`：在Worker环境变量中设置的API密钥
- `config.json` 文件已被添加到 `.gitignore`，不会被提交到版本控制

**网络环境建议：**
- 建议在**原生网络环境**下运行IP优选程序，避免使用代理、VPN等网络加速工具
- 原生网络环境能够确保测试结果真实反映实际网络状况，提高优选IP的可用性和准确性
- 如果必须使用代理环境，请注意优选结果可能与实际使用环境存在差异

## 部署指南

### 1. 部署KV管理API

#### 步骤1：使用原项目的KV空间
如果您已经在使用基于 [cmliu/edgetunnel](https://github.com/cmliu/edgetunnel) 的项目：
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 `Workers & Pages` → `KV`
3. 找到您原项目使用的KV命名空间
4. 记录该KV命名空间的名称，稍后需要绑定到新的Worker（不会两个项目冲突）

如果您是首次使用，需要创建新的KV命名空间并绑定两个项目：
1. 在KV页面点击 `Create a namespace`
2. 输入命名空间名称，例如 `IP_OPTIMIZER`
3. 点击 `Add` 创建

#### 步骤2：部署Workers
1. 进入 `Workers & Pages` → `Create application` → `Create Worker`
2. 将 `kv-manager-worker.js` 的内容复制到编辑器中
3. 点击 `Save and Deploy`

#### 步骤3：绑定KV命名空间（如果第一次使用原项目，请两个项目都按照该步骤绑定）
1. 在Worker设置页面，进入 `Settings` → `Variables`
2. 在 `KV Namespace Bindings` 部分点击 `Add binding`
3. 设置：
   - Variable name: `KV`
   - KV namespace: 选择刚创建的命名空间
4. 点击 `Save and deploy`

**重要提醒：**
- **必须绑定原项目的KV空间**：如果您已经在使用基于 [cmliu/edgetunnel](https://github.com/cmliu/edgetunnel) 的项目，请绑定该项目使用的KV命名空间，以确保IP数据的一致性
- **建议使用自定义域名**：为避免 `*.workers.dev` 域名可能遇到的网络阻断问题，强烈建议为Worker配置自定义域名

#### 步骤4：设置环境变量（鉴权配置）
1. 在Worker设置页面，进入 `Settings` → `Variables`
2. 在 `Environment Variables` 部分点击 `Add variable`
3. 设置：
   - Variable name: `API_KEY`
   - Value: 设置一个强密码作为API访问密钥（例如：`your_secure_api_key_123`）
4. 点击 `Save and deploy`

#### 步骤5：配置自定义域名（推荐）
为避免 `*.workers.dev` 域名的网络阻断问题，建议配置自定义域名：

1. 在Worker设置页面，进入 `Settings` → `Triggers`
2. 在 `Custom Domains` 部分点击 `Add Custom Domain`
3. 输入您的自定义域名（如：`api.yourdomain.com`）
4. 按照提示完成DNS配置
5. 等待SSL证书自动配置完成

#### 步骤6：获取API URL
配置完成后，您可以使用以下URL访问API：

**自定义域名（推荐）：**
```
https://api.yourdomain.com
```

**Workers域名（备用）：**
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
  "ip_count": 0,
  "default_ip_source": "official",
  "default_port": 443,
  "default_action": "replace",
  "worker_url": "https://your-worker.your-subdomain.workers.dev",
  "worker_api_key": "YOUR_WORKER_API_KEY_HERE"
}```

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

### 独立版本（推荐普通用户使用）

独立版本是打包好的单文件可执行程序，无需安装Python环境即可直接运行：

```bash
# Windows系统直接双击运行
dist\CloudflareIPOptimizer.exe

# 或在命令行中运行
cd dist
CloudflareIPOptimizer.exe
```

**独立版本特点：**
- **零依赖**：单个exe文件（约9.5MB），无需安装Python
- **内置配置**：程序内设置参数，无需外部配置文件
- **功能完整**：支持所有核心功能和最新的IP格式
- **操作简便**：图形化界面，一键开始优选
- **实时反馈**：进度显示、日志查看、状态提示

**使用步骤：**
1. 双击运行 `CloudflareIPOptimizer.exe`
2. 点击"配置设置"填入Worker URL和API Key
3. 选择测试参数（端口、IP来源、操作模式）
4. 点击"开始优选"即可自动完成IP测试和上传

**配置说明：**
- **Worker URL**: 您的Cloudflare Worker部署地址
- **API Key**: 在Worker环境变量中设置的API密钥
- **超时时间**: 单次IP测试的超时时间（默认3秒）
- **最大并发数**: 同时测试的IP数量（默认50）
- **测试次数**: 每个IP的测试次数（默认3次）
- **保存IP数量**: 保存到KV的最优IP数量（默认16个）
- **IP数量限制**: 获取IP的数量限制（GUI版本默认500，独立版本默认0不限制）

详细使用说明请参考：[独立版本使用说明.md](独立版本使用说明.md)

### 系统测试

```bash
# 运行完整的系统功能测试
python test_system.py

# 使用自定义配置文件
python test_system.py --config my_config.json

# 指定Worker URL（覆盖配置文件设置）
python test_system.py --worker-url https://your-worker.workers.dev --api-key your-api-key
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
| `--worker-url` | Workers URL | 覆盖配置文件中的设置 |
| `--api-key` | API密钥 | 覆盖配置文件中的设置 |
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
| `worker_url` | Workers地址 | 必填 |
| `worker_api_key` | Workers API密钥 | 必填 |
| `timeout` | 单次连接超时时间（秒） | 3 |
| `max_workers` | 最大并发测试数 | 50 |
| `test_count` | 每个IP测试次数 | 3 |
| `best_count` | 保存的最优IP数量 | 16 |
| `ip_count` | 获取IP数量限制（0表示不限制） | 0 |
| `default_ip_source` | 默认IP来源 | official |
| `default_port` | 默认测试端口 | 443 |
| `default_action` | 默认操作类型 | replace |


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
