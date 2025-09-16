#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统功能测试脚本
用于验证KV管理API和IP优选客户端的功能

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
import json
import logging
from typing import Dict, List

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemTester:
    """系统测试器"""
    
    def __init__(self, worker_url: str, worker_api_key: str):
        self.worker_url = worker_url.rstrip('/')
        self.worker_api_key = worker_api_key
        self.test_results = []
    
    async def test_api_health(self) -> bool:
        """测试API健康检查"""
        logger.info("测试API健康检查...")
        try:
            headers = {'X-API-Key': self.worker_api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.worker_url}/api/health", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success') and data.get('status') == 'healthy':
                            logger.info("API健康检查通过")
                            return True
                        else:
                            logger.error(f"API健康检查失败: {data}")
                            return False
                    else:
                        logger.error(f"API健康检查失败，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"API健康检查异常: {e}")
            return False
    
    async def test_get_ips(self) -> bool:
        """测试获取IP列表"""
        logger.info("测试获取IP列表...")
        try:
            headers = {'X-API-Key': self.worker_api_key}
            async with aiohttp.ClientSession() as session:
                # 测试JSON格式
                async with session.get(f"{self.worker_url}/api/ips?format=json", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success'):
                            ip_count = data.get('data', {}).get('count', 0)
                            logger.info(f"获取IP列表成功，当前有 {ip_count} 个IP")
                            
                            # 测试文本格式
                            async with session.get(f"{self.worker_url}/api/ips?format=text", headers=headers) as text_response:
                                if text_response.status == 200:
                                    text_data = await text_response.text()
                                    logger.info(f"文本格式获取成功，内容长度: {len(text_data)}")
                                    return True
                                else:
                                    logger.error(f"文本格式获取失败，状态码: {text_response.status}")
                                    return False
                        else:
                            logger.error(f"获取IP列表失败: {data.get('error')}")
                            return False
                    else:
                        logger.error(f"获取IP列表失败，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"获取IP列表异常: {e}")
            return False
    
    async def test_update_ips(self) -> bool:
        """测试更新IP列表"""
        logger.info("测试更新IP列表...")
        
        # 测试数据，格式：IP:端口#延迟ms
        test_ips = [
            "1.1.1.1:443#25.67ms",
            "8.8.8.8:443#30.12ms",
            "1.0.0.1:443#28.45ms"
        ]
        
        try:
            headers = {'Content-Type': 'application/json', 'X-API-Key': self.worker_api_key}
            async with aiohttp.ClientSession() as session:
                # 测试替换模式
                data = {
                    "ips": test_ips,
                    "action": "replace",
                    "key": "TEST.txt"
                }
                
                async with session.post(
                    f"{self.worker_url}/api/ips",
                    json=data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            logger.info(f"替换模式更新成功: {result.get('message')}")
                            
                            # 测试追加模式
                            append_ips = ["9.9.9.9:443#22.34ms"]
                            append_data = {
                                "ips": append_ips,
                                "action": "append",
                                "key": "TEST.txt"
                            }
                            
                            async with session.post(
                                f"{self.worker_url}/api/ips",
                                json=append_data,
                                headers=headers
                            ) as append_response:
                                if append_response.status == 200:
                                    append_result = await append_response.json()
                                    if append_result.get('success'):
                                        logger.info(f"追加模式更新成功: {append_result.get('message')}")
                                        return True
                                    else:
                                        logger.error(f"追加模式更新失败: {append_result.get('error')}")
                                        return False
                                else:
                                    logger.error(f"追加模式更新失败，状态码: {append_response.status}")
                                    return False
                        else:
                            logger.error(f"替换模式更新失败: {result.get('error')}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"更新IP列表失败，状态码: {response.status}, 错误: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"更新IP列表异常: {e}")
            return False
    
    async def test_stats(self) -> bool:
        """测试统计信息"""
        logger.info("测试统计信息...")
        try:
            headers = {'X-API-Key': self.worker_api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.worker_url}/api/stats", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success'):
                            stats = data.get('data', {})
                            logger.info(f"统计信息获取成功:")
                            logger.info(f"   - 总IP数: {stats.get('totalIPs')}")
                            logger.info(f"   - 内容大小: {stats.get('contentSizeMB')}MB")
                            logger.info(f"   - 示例IP: {stats.get('sampleIPs')}")
                            return True
                        else:
                            logger.error(f"统计信息获取失败: {data.get('error')}")
                            return False
                    else:
                        logger.error(f"统计信息获取失败，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"统计信息获取异常: {e}")
            return False
    
    async def test_web_interface(self) -> bool:
        """测试Web界面"""
        logger.info("测试Web界面...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.worker_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        if 'Cloudflare IP优选 KV管理API' in html:
                            logger.info("Web界面访问成功")
                            return True
                        else:
                            logger.error("Web界面内容异常")
                            return False
                    else:
                        logger.error(f"Web界面访问失败，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Web界面访问异常: {e}")
            return False
    
    async def test_ip_optimization_simulation(self) -> bool:
        """模拟IP优选流程测试"""
        logger.info("模拟IP优选流程测试...")
        
        # 模拟优选结果，格式：IP:端口#延迟ms
        optimized_ips = [
            "104.16.1.1:443#15.23ms",
            "104.16.2.2:443#18.45ms",
            "104.16.3.3:443#20.67ms",
            "172.64.1.1:443#22.89ms",
            "172.64.2.2:443#25.12ms"
        ]
        
        try:
            # 1. 获取当前IP列表
            headers = {'X-API-Key': self.worker_api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.worker_url}/api/ips?format=json", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success'):
                            current_count = data.get('data', {}).get('count', 0)
                            logger.info(f"当前IP数量: {current_count}")
                        else:
                            logger.warning("无法获取当前IP列表")
                    else:
                        logger.warning("无法获取当前IP列表")
                
                # 2. 上传优选结果（追加模式）
                upload_data = {
                    "ips": optimized_ips,
                    "action": "append",
                    "key": "ADD.txt"
                }
                
                async with session.post(
                    f"{self.worker_url}/api/ips",
                    json=upload_data,
                    headers={'Content-Type': 'application/json', 'X-API-Key': self.worker_api_key}
                ) as upload_response:
                    if upload_response.status == 200:
                        result = await upload_response.json()
                        if result.get('success'):
                            logger.info(f"模拟优选上传成功: {result.get('message')}")
                            
                            # 3. 验证上传结果
                            async with session.get(f"{self.worker_url}/api/stats", headers=headers) as stats_response:
                                if stats_response.status == 200:
                                    stats_data = await stats_response.json()
                                    if stats_data.get('success'):
                                        new_count = stats_data.get('data', {}).get('totalIPs', 0)
                                        logger.info(f"上传后IP数量: {new_count}")
                                        return True
                            
                            return True
                        else:
                            logger.error(f"模拟优选上传失败: {result.get('error')}")
                            return False
                    else:
                        error_text = await upload_response.text()
                        logger.error(f"模拟优选上传失败，状态码: {upload_response.status}, 错误: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"模拟IP优选流程异常: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始系统功能测试")
        logger.info(f"Worker URL: {self.worker_url}")
        logger.info("=" * 60)
        
        tests = [
            ("API健康检查", self.test_api_health),
            ("Web界面访问", self.test_web_interface),
            ("获取IP列表", self.test_get_ips),
            ("更新IP列表", self.test_update_ips),
            ("统计信息", self.test_stats),
            ("IP优选流程模拟", self.test_ip_optimization_simulation)
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = await test_func()
                results[test_name] = result
                if result:
                    passed += 1
            except Exception as e:
                logger.error(f"{test_name} 测试异常: {e}")
                results[test_name] = False
        
        # 输出测试总结
        logger.info("\n" + "=" * 60)
        logger.info("测试结果总结")
        logger.info("=" * 60)
        
        for test_name, result in results.items():
            status = "通过" if result else "失败"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\n总计: {passed}/{total} 个测试通过")
        
        if passed == total:
            logger.info("所有测试都通过了！系统功能正常。")
        else:
            logger.warning(f"有 {total - passed} 个测试失败，请检查相关功能。")
        
        logger.info("=" * 60)
        
        return results

def load_config(config_file: str = 'config.json') -> Dict:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"配置文件 {config_file} 不存在")
        return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='系统功能测试')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--worker-url', help='Worker URL（覆盖配置文件）')
    parser.add_argument('--api-key', help='API密钥（覆盖配置文件）')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 获取Worker URL和API密钥
    worker_url = args.worker_url or config.get('worker_url')
    worker_api_key = args.api_key or config.get('worker_api_key')
    
    if not worker_url:
        logger.error("请在配置文件中设置worker_url或使用--worker-url参数")
        return
    
    if not worker_api_key:
        logger.error("请在配置文件中设置worker_api_key或使用--api-key参数")
        return
    
    # 运行测试
    tester = SystemTester(worker_url, worker_api_key)
    results = await tester.run_all_tests()
    
    # 返回退出码
    failed_count = sum(1 for result in results.values() if not result)
    exit(failed_count)

if __name__ == '__main__':
    asyncio.run(main())