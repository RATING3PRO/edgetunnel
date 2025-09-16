/**
 * Cloudflare Workers KV管理API
 * 用于管理IP优选列表的KV存储
 * 
 * Copyright (C) 2024
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // CORS处理
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
      'Access-Control-Max-Age': '86400',
    };

// 鉴权验证函数
async function authenticateRequest(request, env) {
  try {
    // 从环境变量获取API密钥
    const validApiKey = env.API_KEY;
    
    // 如果未设置API密钥，则拒绝访问
    if (!validApiKey) {
      return {
        success: false,
        error: '服务器未配置API密钥，请联系管理员设置 API_KEY 环境变量'
      };
    }
    
    // 从请求头获取API密钥
    const providedKey = request.headers.get('X-API-Key') || 
                       request.headers.get('Authorization')?.replace('Bearer ', '') ||
                       new URL(request.url).searchParams.get('api_key');
    
    if (!providedKey) {
      return {
        success: false,
        error: '缺少API密钥，请在请求头中提供 X-API-Key 或 Authorization，或在URL参数中提供 api_key'
      };
    }
    
    // 验证API密钥
    if (providedKey !== validApiKey) {
      return {
        success: false,
        error: 'API密钥无效，访问被拒绝'
      };
    }
    
    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: '鉴权验证失败: ' + error.message
    };
  }
}

    // 处理预检请求
    if (method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders
      });
    }

    try {
      // 检查KV绑定
      if (!env.KV) {
        return new Response(JSON.stringify({
          success: false,
          error: '未绑定KV空间，请在Workers设置中绑定KV命名空间'
        }), {
          status: 500,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }

      // 鉴权验证（除了首页和健康检查）
      if (path !== '/' && path !== '/api/health') {
        const authResult = await authenticateRequest(request, env);
        if (!authResult.success) {
          return new Response(JSON.stringify({
            success: false,
            error: authResult.error
          }), {
            status: 401,
            headers: {
              'Content-Type': 'application/json',
              ...corsHeaders
            }
          });
        }
      }

      // API路由处理
      if (path === '/api/ips' && method === 'GET') {
        return await getIPs(env, url, corsHeaders);
      } else if (path === '/api/ips' && method === 'POST') {
        return await updateIPs(request, env, corsHeaders);
      } else if (path === '/api/health' && method === 'GET') {
        return await healthCheck(env, corsHeaders);
      } else if (path === '/api/stats' && method === 'GET') {
        return await getStats(env, corsHeaders);
      } else if (path === '/' && method === 'GET') {
        return await getHomePage(corsHeaders);
      } else {
        return new Response(JSON.stringify({
          success: false,
          error: '未找到请求的API端点'
        }), {
          status: 404,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
    } catch (error) {
      console.error('处理请求时发生错误:', error);
      return new Response(JSON.stringify({
        success: false,
        error: '服务器内部错误: ' + error.message
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
  }
};

// 获取IP列表
async function getIPs(env, url, corsHeaders) {
  try {
    const key = url.searchParams.get('key') || 'ADD.txt';
    const format = url.searchParams.get('format') || 'json';
    
    const content = await env.KV.get(key) || '';
    const ips = content ? content.split('\n').filter(line => line.trim()) : [];
    
    if (format === 'text') {
      return new Response(content, {
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          ...corsHeaders
        }
      });
    }
    
    return new Response(JSON.stringify({
      success: true,
      data: {
        key: key,
        count: ips.length,
        ips: ips,
        lastUpdated: new Date().toISOString()
      }
    }), {
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  } catch (error) {
    console.error('获取IP列表失败:', error);
    return new Response(JSON.stringify({
      success: false,
      error: '获取IP列表失败: ' + error.message
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  }
}

// 更新IP列表
async function updateIPs(request, env, corsHeaders) {
  try {
    const contentType = request.headers.get('Content-Type');
    let data;
    
    if (contentType && contentType.includes('application/json')) {
      data = await request.json();
    } else {
      // 兼容文本格式
      const text = await request.text();
      data = {
        ips: text.split('\n').filter(line => line.trim()),
        action: 'replace',
        key: 'ADD.txt'
      };
    }
    
    const { ips, action = 'replace', key = 'ADD.txt' } = data;
    
    if (!ips || !Array.isArray(ips)) {
      return new Response(JSON.stringify({
        success: false,
        error: 'IP列表格式错误，需要提供ips数组'
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
    
    let finalIPs = [];
    let message = '';
    
    if (action === 'append') {
      // 追加模式
      const existingContent = await env.KV.get(key) || '';
      const existingIPs = existingContent ? 
        existingContent.split('\n').filter(line => line.trim()) : [];
      
      // 合并并去重
      const allIPs = [...existingIPs, ...ips];
      finalIPs = [...new Set(allIPs)];
      
      const addedCount = finalIPs.length - existingIPs.length;
      const duplicateCount = ips.length - addedCount;
      
      message = `成功追加 ${addedCount} 个新IP（原有 ${existingIPs.length} 个，现共 ${finalIPs.length} 个）`;
      if (duplicateCount > 0) {
        message += `，已去重 ${duplicateCount} 个重复项`;
      }
    } else {
      // 替换模式
      finalIPs = [...new Set(ips)]; // 去重
      message = `成功保存 ${finalIPs.length} 个IP`;
    }
    
    const content = finalIPs.join('\n');
    
    // 检查内容大小（KV限制为25MB）
    if (content.length > 24 * 1024 * 1024) {
      return new Response(JSON.stringify({
        success: false,
        error: `内容过大（${(content.length / 1024 / 1024).toFixed(2)}MB），超过KV存储限制（24MB）`
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
    
    await env.KV.put(key, content);
    
    return new Response(JSON.stringify({
      success: true,
      message: message,
      data: {
        key: key,
        count: finalIPs.length,
        action: action,
        timestamp: new Date().toISOString()
      }
    }), {
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  } catch (error) {
    console.error('更新IP列表失败:', error);
    return new Response(JSON.stringify({
      success: false,
      error: '更新IP列表失败: ' + error.message
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  }
}

// 健康检查
async function healthCheck(env, corsHeaders) {
  try {
    // 测试KV连接
    const testKey = 'health_check_' + Date.now();
    await env.KV.put(testKey, 'test', { expirationTtl: 60 }); // 60秒后过期
    const testValue = await env.KV.get(testKey);
    await env.KV.delete(testKey);
    
    const isKVHealthy = testValue === 'test';
    
    return new Response(JSON.stringify({
      success: true,
      status: 'healthy',
      timestamp: new Date().toISOString(),
      services: {
        kv: isKVHealthy ? 'healthy' : 'unhealthy'
      }
    }), {
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  } catch (error) {
    console.error('健康检查失败:', error);
    return new Response(JSON.stringify({
      success: false,
      status: 'unhealthy',
      error: error.message,
      timestamp: new Date().toISOString()
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  }
}

// 获取统计信息
async function getStats(env, corsHeaders) {
  try {
    const key = 'ADD.txt';
    const content = await env.KV.get(key) || '';
    const ips = content ? content.split('\n').filter(line => line.trim()) : [];
    
    // 分析IP统计
    const stats = {
      totalIPs: ips.length,
      contentSize: content.length,
      contentSizeMB: (content.length / 1024 / 1024).toFixed(2),
      lastUpdated: new Date().toISOString(),
      sampleIPs: ips.slice(0, 5) // 前5个IP作为示例
    };
    
    return new Response(JSON.stringify({
      success: true,
      data: stats
    }), {
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  } catch (error) {
    console.error('获取统计信息失败:', error);
    return new Response(JSON.stringify({
      success: false,
      error: '获取统计信息失败: ' + error.message
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders
      }
    });
  }
}

// 首页
async function getHomePage(corsHeaders) {
  const html = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloudflare IP优选 KV管理API</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .api-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .endpoint {
            background: white;
            padding: 15px;
            border-left: 4px solid #007bff;
            margin: 10px 0;
            border-radius: 4px;
        }
        .method {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            margin-right: 10px;
        }
        .get { background: #28a745; color: white; }
        .post { background: #007bff; color: white; }
        code {
            background: #f1f3f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        .example {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .status {
            text-align: center;
            padding: 20px;
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            color: #155724;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Cloudflare IP优选 KV管理API</h1>
        <p>用于管理优选IP列表的RESTful API服务</p>
    </div>
    
    <div class="status">
        <h3>服务状态：正常运行</h3>
        <p>KV命名空间已成功绑定，API服务可用</p>
    </div>
    
    <div class="api-section">
        <h2>API接口文档</h2>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/ips</strong>
            <p>获取当前的IP列表</p>
            <p><strong>参数：</strong></p>
            <ul>
                <li><code>key</code> (可选): KV键名，默认为 'ADD.txt'</li>
                <li><code>format</code> (可选): 返回格式 'json' 或 'text'，默认为 'json'</li>
            </ul>
            <div class="example">
                <strong>示例：</strong><br>
                <code>GET /api/ips?format=json</code><br>
                <code>GET /api/ips?key=ADD.txt&format=text</code>
            </div>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/api/ips</strong>
            <p>更新IP列表</p>
            <p><strong>请求体 (JSON)：</strong></p>
            <div class="example">
                <pre>{
  "ips": ["1.1.1.1", "8.8.8.8"],
  "action": "replace", // 或 "append"
  "key": "ADD.txt" // 可选
}</pre>
            </div>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/health</strong>
            <p>健康检查，测试KV连接状态</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/stats</strong>
            <p>获取IP列表统计信息</p>
        </div>
    </div>
    
    <div class="api-section">
        <h2>使用说明</h2>
        <ol>
            <li>确保已在Cloudflare Workers中绑定KV命名空间，变量名为 <code>KV</code></li>
            <li><strong>重要：</strong>在Workers环境变量中设置 <code>API_KEY</code> 作为访问密钥</li>
            <li>除首页和健康检查外，所有API都需要提供API密钥进行鉴权</li>
            <li>API密钥可通过以下方式提供：
                <ul>
                    <li>请求头：<code>X-API-Key: your_api_key</code></li>
                    <li>Authorization头：<code>Authorization: Bearer your_api_key</code></li>
                    <li>URL参数：<code>?api_key=your_api_key</code></li>
                </ul>
            </li>
            <li>所有API都支持CORS，可以从任何域名访问</li>
            <li>IP列表以换行符分隔存储在KV中</li>
            <li>支持追加和替换两种更新模式</li>
            <li>自动去重处理</li>
        </ol>
    </div>
    
    <div class="api-section">
        <h2>安全配置</h2>
        <div class="example">
            <p><strong>在Cloudflare Workers中设置环境变量：</strong></p>
            <ol>
                <li>进入Workers控制台，选择您的Worker</li>
                <li>点击 "Settings" → "Variables"</li>
                <li>添加环境变量：
                    <ul>
                        <li>变量名：<code>API_KEY</code></li>
                        <li>值：您的自定义API密钥（建议使用强密码）</li>
                    </ul>
                </li>
                <li>保存并重新部署Worker</li>
            </ol>
        </div>
    </div>
    
    <div class="api-section">
        <h2>快速测试</h2>
        <p>点击以下链接测试API：</p>
        <ul>
            <li><a href="/api/health" target="_blank">健康检查</a></li>
            <li><a href="/api/stats" target="_blank">统计信息</a></li>
            <li><a href="/api/ips?format=json" target="_blank">获取IP列表 (JSON)</a></li>
            <li><a href="/api/ips?format=text" target="_blank">获取IP列表 (文本)</a></li>
        </ul>
    </div>
</body>
</html>
  `;
  
  return new Response(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      ...corsHeaders
    }
  });
}