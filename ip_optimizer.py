#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare IP优选客户端
本地测速并上传优选结果到KV空间

Copyright (C) 2024

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import asyncio
import aiohttp
import time
import json
import logging
import argparse
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import socket
import ssl
import ipaddress
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ip_optimizer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class IPTestResult:
    """IP测试结果"""
    ip: str
    port: int
    latency: float  # 延迟，-1表示失败
    success: bool
    error: Optional[str] = None

class CloudflareIPOptimizer:
    """Cloudflare IP优选器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.worker_url = config.get('worker_url', '').rstrip('/')
        self.worker_api_key = config.get('worker_api_key', '')
        self.timeout = config.get('timeout', 3)
        self.max_workers = config.get('max_workers', 50)
        self.test_count = config.get('test_count', 3)
        self.best_count = config.get('best_count', 16)
        
        # 验证Worker URL和API密钥
        if not self.worker_url:
            raise ValueError("Worker URL不能为空")
        if not self.worker_api_key:
            raise ValueError("Worker API密钥不能为空")
        
        try:
            parsed = urlparse(self.worker_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Worker URL格式无效")
        except Exception as e:
            raise ValueError(f"Worker URL格式错误: {e}")
    
    async def get_cf_ips(self, ip_source: str = 'official') -> List[str]:
        """获取Cloudflare IP列表"""
        logger.info(f"正在获取IP列表，来源: {ip_source}")
        
        ip_sources = {
            'official': 'https://www.cloudflare.com/ips-v4/',
            'cm': 'https://raw.githubusercontent.com/cmliu/cmliu/main/CF-CIDR.txt',
            'as13335': 'https://raw.githubusercontent.com/ipverse/asn-ip/master/as/13335/ipv4-aggregated.txt',
            'as209242': 'https://raw.githubusercontent.com/ipverse/asn-ip/master/as/209242/ipv4-aggregated.txt',
            'proxyip': 'https://raw.githubusercontent.com/cmliu/ACL4SSR/main/baipiao.txt'
        }
        
        url = ip_sources.get(ip_source, ip_sources['official'])
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_ip_list(content, ip_source)
                    else:
                        logger.error(f"获取IP列表失败，状态码: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"获取IP列表异常: {e}")
            return []
    
    def _parse_ip_list(self, content: str, ip_source: str) -> List[str]:
        """解析IP列表"""
        ips = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ip_source == 'proxyip':
                # 解析反代IP格式
                ip = self._parse_proxyip_line(line)
                if ip:
                    ips.append(ip)
            else:
                # 解析CIDR格式
                if '/' in line:
                    # CIDR格式，生成随机IP
                    generated_ips = self._generate_ips_from_cidr(line, 10)
                    ips.extend(generated_ips)
                else:
                    # 直接IP
                    if self._is_valid_ip(line):
                        ips.append(line)
        
        # 去重并限制数量
        unique_ips = list(set(ips))
        ip_count = self.config.get('ip_count', 0)
        if ip_count > 0 and len(unique_ips) > ip_count:
            import random
            unique_ips = random.sample(unique_ips, ip_count)
        
        logger.info(f"解析得到 {len(unique_ips)} 个有效IP")
        return unique_ips
    
    def _parse_proxyip_line(self, line: str) -> Optional[str]:
        """解析反代IP行"""
        try:
            # 移除注释
            if '#' in line:
                line = line.split('#')[0].strip()
            
            # 提取IP
            if ':' in line:
                ip = line.split(':')[0].strip()
            else:
                ip = line.strip()
            
            return ip if self._is_valid_ip(ip) else None
        except:
            return None
    
    def _generate_ips_from_cidr(self, cidr: str, count: int = 10) -> List[str]:
        """从CIDR生成随机IP"""
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            hosts = list(network.hosts())
            
            if len(hosts) == 0:
                return []
            
            import random
            sample_count = min(count, len(hosts))
            selected_hosts = random.sample(hosts, sample_count)
            
            return [str(ip) for ip in selected_hosts]
        except Exception as e:
            logger.warning(f"解析CIDR {cidr} 失败: {e}")
            return []
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            ipaddress.IPv4Address(ip)
            return True
        except:
            return False
    
    def test_ip_latency(self, ip: str, port: int = 443) -> IPTestResult:
        """测试单个IP的延迟"""
        total_time = 0
        success_count = 0
        
        for i in range(self.test_count):
            try:
                start_time = time.time()
                
                # 创建SSL上下文
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                # 创建socket连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                
                try:
                    # 连接
                    sock.connect((ip, port))
                    
                    # 如果是443端口，进行SSL握手
                    if port == 443:
                        ssl_sock = context.wrap_socket(sock, server_hostname='cloudflare.com')
                        ssl_sock.close()
                    else:
                        sock.close()
                    
                    end_time = time.time()
                    latency = (end_time - start_time) * 1000  # 转换为毫秒
                    total_time += latency
                    success_count += 1
                    
                except Exception as e:
                    sock.close()
                    if i == self.test_count - 1:  # 最后一次尝试
                        return IPTestResult(ip, port, -1, False, str(e))
                    continue
                    
            except Exception as e:
                if i == self.test_count - 1:  # 最后一次尝试
                    return IPTestResult(ip, port, -1, False, str(e))
                continue
        
        if success_count > 0:
            avg_latency = total_time / success_count
            return IPTestResult(ip, port, round(avg_latency, 2), True)
        else:
            return IPTestResult(ip, port, -1, False, "所有测试都失败")
    
    async def test_ips_batch(self, ips: List[str], port: int = 443) -> List[IPTestResult]:
        """批量测试IP延迟"""
        logger.info(f"开始测试 {len(ips)} 个IP的延迟，端口: {port}")
        
        results = []
        
        # 使用线程池进行并发测试
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()
            
            # 创建任务
            tasks = []
            for i, ip in enumerate(ips):
                task = loop.run_in_executor(executor, self.test_ip_latency, ip, port)
                tasks.append(task)
                
                # 每50个IP显示一次进度
                if (i + 1) % 50 == 0 or i == len(ips) - 1:
                    logger.info(f"已创建 {i + 1}/{len(ips)} 个测试任务")
            
            # 等待所有任务完成
            logger.info("正在执行延迟测试...")
            results = await asyncio.gather(*tasks)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        logger.info(f"测试完成，成功: {success_count}/{len(results)}")
        
        return results
    
    def get_best_ips(self, results: List[IPTestResult]) -> List[str]:
        """获取最优IP列表"""
        # 过滤成功的结果并按延迟排序
        successful_results = [r for r in results if r.success and r.latency > 0]
        successful_results.sort(key=lambda x: x.latency)
        
        # 取前N个最优IP
        best_results = successful_results[:self.best_count]
        best_ips = [f"{r.ip}:{r.port}#{r.latency:.2f}ms" for r in best_results]
        
        logger.info(f"选出 {len(best_ips)} 个最优IP")
        for i, result in enumerate(best_results[:10]):  # 显示前10个
            logger.info(f"  {i+1}. {result.ip}:{result.port} - {result.latency}ms")
        
        return best_ips
    
    async def upload_ips(self, ips: List[str], action: str = 'replace') -> bool:
        """上传IP列表到KV空间"""
        if not ips:
            logger.warning("没有IP需要上传")
            return False
        
        logger.info(f"正在上传 {len(ips)} 个IP到KV空间，操作: {action}")
        
        data = {
            'ips': ips,
            'action': action,
            'key': 'ADD.txt'
        }
        
        # 准备鉴权头
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.worker_api_key
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post(
                    f"{self.worker_url}/api/ips",
                    json=data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            logger.info(f"上传成功: {result.get('message')}")
                            return True
                        else:
                            logger.error(f"上传失败: {result.get('error')}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"上传失败，状态码: {response.status}, 错误: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"上传异常: {e}")
            return False
    
    async def get_current_ips(self) -> List[str]:
        """获取当前KV中的IP列表"""
        try:
            headers = {'X-API-Key': self.worker_api_key}
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(f"{self.worker_url}/api/ips?format=json", headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            return result.get('data', {}).get('ips', [])
                    return []
        except Exception as e:
            logger.error(f"获取当前IP列表失败: {e}")
            return []
    
    async def run_optimization(self, ip_source: str = 'official', port: int = 443, action: str = 'replace'):
        """运行完整的IP优选流程"""
        logger.info("=" * 50)
        logger.info("开始Cloudflare IP优选")
        logger.info(f"配置: 来源={ip_source}, 端口={port}, 操作={action}")
        logger.info("=" * 50)
        
        try:
            # 1. 获取IP列表
            ips = await self.get_cf_ips(ip_source)
            if not ips:
                logger.error("未能获取到IP列表")
                return False
            
            # 2. 测试IP延迟
            results = await self.test_ips_batch(ips, port)
            
            # 3. 获取最优IP
            best_ips = self.get_best_ips(results)
            if not best_ips:
                logger.error("未找到可用的IP")
                return False
            
            # 4. 上传到KV空间
            success = await self.upload_ips(best_ips, action)
            
            if success:
                logger.info("=" * 50)
                logger.info("IP优选完成！")
                logger.info("=" * 50)
                return True
            else:
                logger.error("IP优选失败")
                return False
                
        except Exception as e:
            logger.error(f"优选过程中发生异常: {e}")
            return False

def load_config(config_file: str = 'config.json') -> Dict:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
        return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def create_default_config(config_file: str = 'config.json'):
    """创建默认配置文件"""
    default_config = {
        "worker_url": "https://your-worker.your-subdomain.workers.dev",
        "worker_api_key": "your-api-key-here",
        "timeout": 3,
        "max_workers": 50,
        "test_count": 3,
        "best_count": 16,
        "default_ip_source": "official",
        "default_port": 443,
        "default_action": "replace"
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        logger.info(f"已创建默认配置文件: {config_file}")
    except Exception as e:
        logger.error(f"创建配置文件失败: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Cloudflare IP优选客户端')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--worker-url', help='Workers URL')
    parser.add_argument('--api-key', help='API密钥')
    parser.add_argument('--source', choices=['official', 'cm', 'as13335', 'as209242', 'proxyip'], 
                       help='IP来源')
    parser.add_argument('--port', type=int, choices=[443, 2053, 2083, 2087, 2096, 8443], 
                       help='测试端口')
    parser.add_argument('--action', choices=['replace', 'append'], help='上传操作类型')
    parser.add_argument('--create-config', action='store_true', help='创建默认配置文件')
    
    args = parser.parse_args()
    
    # 创建默认配置文件
    if args.create_config:
        create_default_config(args.config)
        return
    
    # 加载配置
    config = load_config(args.config)
    
    # 命令行参数覆盖配置文件
    if args.worker_url:
        config['worker_url'] = args.worker_url
    if args.api_key:
        config['worker_api_key'] = args.api_key
    if args.source:
        config['default_ip_source'] = args.source
    if args.port:
        config['default_port'] = args.port
    if args.action:
        config['default_action'] = args.action
    
    # 检查必要配置
    if not config.get('worker_url'):
        logger.error("请在配置文件中设置worker_url或使用--worker-url参数")
        logger.info("使用 --create-config 创建默认配置文件")
        return
    if not config.get('worker_api_key'):
        logger.error("请在配置文件中设置worker_api_key或使用--api-key参数")
        logger.info("使用 --create-config 创建默认配置文件")
        return
    
    try:
        # 创建优选器并运行
        optimizer = CloudflareIPOptimizer(config)
        
        ip_source = config.get('default_ip_source', 'official')
        port = config.get('default_port', 443)
        action = config.get('default_action', 'replace')
        
        await optimizer.run_optimization(ip_source, port, action)
        
    except Exception as e:
        logger.error(f"程序运行异常: {e}")

if __name__ == '__main__':
    asyncio.run(main())