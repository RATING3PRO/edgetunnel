#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare IP优选器 - GUI版本
基于tkinter的图形界面，支持端口选择、IP来源选择和自定义IP上传功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import socket
import ssl

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class IPResult:
    """IP测试结果"""
    ip: str
    port: int
    latency: float
    success: bool
    error: Optional[str] = None

class CloudflareIPOptimizerGUI:
    """Cloudflare IP优选器GUI类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Cloudflare IP优选器")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # 配置变量
        self.config = self.load_config()
        
        # GUI变量
        self.port_var = tk.StringVar(value="443")
        self.source_var = tk.StringVar(value="official")
        self.test_count_var = tk.StringVar(value="10")
        self.timeout_var = tk.StringVar(value="3")
        self.max_workers_var = tk.StringVar(value="50")
        self.operation_var = tk.StringVar(value="replace")
        self.ip_count_var = tk.StringVar(value="500")
        
        # 状态变量
        self.is_running = False
        self.results = []
        
        # 创建GUI界面
        self.create_widgets()
        
        # 重定向日志到GUI
        self.setup_logging()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {
                "worker_url": "",
                "worker_api_key": ""
            }
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # 标题
        title_label = ttk.Label(main_frame, text="Cloudflare IP优选器", font=('Arial', 16, 'bold'))
        title_label.grid(row=row, column=0, columnspan=2, pady=(0, 20))
        row += 1
        
        # 端口选择
        ttk.Label(main_frame, text="测试端口:").grid(row=row, column=0, sticky=tk.W, pady=5)
        port_frame = ttk.Frame(main_frame)
        port_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ports = ["443", "80", "2053", "2083", "2087", "2096", "8443", "8880"]
        for i, port in enumerate(ports):
            ttk.Radiobutton(port_frame, text=port, variable=self.port_var, value=port).grid(row=0, column=i, padx=5)
        row += 1
        
        # IP来源选择
        ttk.Label(main_frame, text="IP来源:").grid(row=row, column=0, sticky=tk.W, pady=5)
        source_frame = ttk.Frame(main_frame)
        source_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 数据源选项
        self.ip_sources = {
            "official": "Cloudflare官方",
            "cm": "CM Liu维护",
            "as13335": "ASN 13335",
            "as209242": "ASN 209242", 
            "proxyip": "反代IP列表",
            "custom": "自定义IP"
        }
        
        self.source_combo = ttk.Combobox(source_frame, values=list(self.ip_sources.values()), 
                                        state="readonly", width=20)
        self.source_combo.grid(row=0, column=0, padx=5)
        self.source_combo.set(self.ip_sources[self.source_var.get()])
        self.source_combo.bind('<<ComboboxSelected>>', self.on_source_changed)
        row += 1
        
        # 自定义IP输入区域
        ttk.Label(main_frame, text="自定义IP列表:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5)
        ip_frame = ttk.Frame(main_frame)
        ip_frame.grid(row=row, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        ip_frame.columnconfigure(0, weight=1)
        
        self.custom_ip_text = scrolledtext.ScrolledText(ip_frame, height=6, width=50)
        self.custom_ip_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        
        # 初始状态设置
        if self.source_var.get() != "custom":
            self.custom_ip_text.config(state='disabled')
        
        ttk.Button(ip_frame, text="从文件导入", command=self.import_ip_file).grid(row=1, column=0, sticky=tk.W)
        ttk.Button(ip_frame, text="清空", command=self.clear_custom_ips).grid(row=1, column=1, sticky=tk.E)
        row += 1
        
        # 测试参数
        params_frame = ttk.LabelFrame(main_frame, text="测试参数", padding="10")
        params_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        params_frame.columnconfigure(1, weight=1)
        
        ttk.Label(params_frame, text="选取数量:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.test_count_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Label(params_frame, text="超时时间(秒):").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(20, 0))
        ttk.Entry(params_frame, textvariable=self.timeout_var, width=10).grid(row=0, column=3, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Label(params_frame, text="并发数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.max_workers_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Label(params_frame, text="上传模式:").grid(row=1, column=2, sticky=tk.W, pady=2, padx=(20, 0))
        operation_combo = ttk.Combobox(params_frame, textvariable=self.operation_var, values=["replace", "append"], width=10, state="readonly")
        operation_combo.grid(row=1, column=3, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Label(params_frame, text="IP数量限制:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ip_count_entry = ttk.Entry(params_frame, textvariable=self.ip_count_var, width=10)
        ip_count_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Label(params_frame, text="个（0表示不限制）").grid(row=2, column=2, columnspan=2, sticky=tk.W, pady=2, padx=(5, 0))
        row += 1
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始优选", command=self.start_optimization)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_optimization, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).grid(row=0, column=2, padx=5)
        row += 1
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5")
        log_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def setup_logging(self):
        """设置日志重定向到GUI"""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.config(state='normal')
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                    self.text_widget.config(state='disabled')
                self.text_widget.after(0, append)
        
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_handler)
    
    def import_ip_file(self):
        """从文件导入IP列表"""
        file_path = filedialog.askopenfilename(
            title="选择IP列表文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.custom_ip_text.delete(1.0, tk.END)
                self.custom_ip_text.insert(1.0, content)
                logger.info(f"已导入IP文件: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导入文件失败: {e}")
    
    def clear_custom_ips(self):
        """清空自定义IP列表"""
        self.custom_ip_text.delete(1.0, tk.END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def on_source_changed(self, event=None):
        """IP来源选择变化回调"""
        selected_text = self.source_combo.get()
        # 根据显示文本找到对应的键值
        for key, value in self.ip_sources.items():
            if value == selected_text:
                self.source_var.set(key)
                break
        
        # 根据选择显示/隐藏自定义IP输入框
        if self.source_var.get() == "custom":
            self.custom_ip_text.config(state='normal')
        else:
            self.custom_ip_text.config(state='disabled')
    
    def start_optimization(self):
        """开始IP优选"""
        if self.is_running:
            return
        
        # 验证配置
        if not self.config.get('worker_url') or not self.config.get('worker_api_key'):
            messagebox.showerror("配置错误", "请先配置Worker URL和API密钥")
            return
        
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress.start()
        
        # 在新线程中运行优选
        thread = threading.Thread(target=self.run_optimization)
        thread.daemon = True
        thread.start()
    
    def stop_optimization(self):
        """停止IP优选"""
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress.stop()
        logger.info("用户停止了优选过程")
    
    def run_optimization(self):
        """运行IP优选的主逻辑"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步优选
            loop.run_until_complete(self.async_optimization())
            
        except Exception as e:
            logger.error(f"优选过程出错: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: (
                self.start_button.config(state="normal"),
                self.stop_button.config(state="disabled"),
                self.progress.stop()
            ))
    
    async def async_optimization(self):
        """异步IP优选逻辑"""
        logger.info("=" * 50)
        logger.info("开始Cloudflare IP优选")
        logger.info(f"配置: 端口={self.port_var.get()}, 来源={self.source_var.get()}, 选取数量={self.test_count_var.get()}")
        logger.info("=" * 50)
        
        # 获取IP列表
        ips = await self.get_ip_list()
        if not ips:
            logger.error("未获取到有效IP列表")
            return
        
        logger.info(f"获取到 {len(ips)} 个IP地址")
        
        # 测试IP延迟
        port = int(self.port_var.get())
        timeout = float(self.timeout_var.get())
        max_workers = int(self.max_workers_var.get())
        
        results = await self.test_ips_latency(ips, port, timeout, max_workers)
        
        if not results:
            logger.error("没有测试成功的IP")
            return
        
        # 选择最优IP
        test_count = int(self.test_count_var.get())
        best_ips = sorted(results, key=lambda x: x.latency)[:test_count]
        
        logger.info(f"选出 {len(best_ips)} 个最优IP")
        for i, result in enumerate(best_ips, 1):
            logger.info(f"  {i}. {result.ip}:{result.port} - {result.latency:.2f}ms")
        
        # 上传到KV
        await self.upload_ips(best_ips)
        
        logger.info("=" * 50)
        logger.info("IP优选完成！")
        logger.info("=" * 50)
    
    async def get_ip_list(self) -> List[str]:
        """获取IP列表"""
        source = self.source_var.get()
        
        if source == "custom":
            # 自定义IP列表
            custom_text = self.custom_ip_text.get(1.0, tk.END).strip()
            if not custom_text:
                logger.error("自定义IP列表为空")
                return []
            
            ips = []
            for line in custom_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 验证IP格式
                    try:
                        ipaddress.ip_address(line)
                        ips.append(line)
                    except ValueError:
                        logger.warning(f"无效IP地址: {line}")
            
            logger.info(f"解析得到 {len(ips)} 个有效IP")
            return ips
        
        else:
            # 根据不同数据源获取IP列表
            urls = {
                "official": "https://www.cloudflare.com/ips-v4",
                "cm": "https://raw.githubusercontent.com/cmliu/cmliu/main/CF-CIDR.txt",
                "as13335": "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/13335/ipv4-aggregated.txt",
                "as209242": "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/209242/ipv4-aggregated.txt",
                "proxyip": "https://raw.githubusercontent.com/cmliu/ACL4SSR/main/baipiao.txt"
            }
            
            url = urls.get(source, urls["official"])
            logger.info(f"正在获取IP列表: {self.ip_sources[source]}...")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # 统一处理不同格式的IP数据
                            ips = []
                            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                            
                            for line in lines:
                                if '/' in line:
                                    # CIDR格式，生成随机IP
                                    try:
                                        network = ipaddress.ip_network(line, strict=False)
                                        # 从每个网段中选择一些IP
                                        hosts = list(network.hosts())
                                        if hosts:
                                            import random
                                            count = min(10, len(hosts))
                                            selected_hosts = random.sample(hosts, count)
                                            ips.extend([str(ip) for ip in selected_hosts])
                                    except ValueError:
                                        continue
                                else:
                                    # 直接IP地址
                                    try:
                                        ipaddress.ip_address(line)
                                        ips.append(line)
                                    except ValueError:
                                        continue
                            
                            # 去重并限制数量
                            ips = list(set(ips))
                            ip_limit = int(self.ip_count_var.get())
                            if ip_limit > 0 and len(ips) > ip_limit:
                                import random
                                ips = random.sample(ips, ip_limit)
                            
                            logger.info(f"解析得到 {len(ips)} 个有效IP")
                            return ips
                        else:
                            logger.error(f"获取IP列表失败: HTTP {response.status}")
                            return []
            except Exception as e:
                logger.error(f"获取IP列表出错: {e}")
                return []
    
    async def test_ips_latency(self, ips: List[str], port: int, timeout: float, max_workers: int) -> List[IPResult]:
        """测试IP延迟"""
        logger.info(f"开始测试 {len(ips)} 个IP的延迟，端口: {port}")
        
        results = []
        semaphore = asyncio.Semaphore(max_workers)
        
        async def test_single_ip(ip: str) -> Optional[IPResult]:
            if not self.is_running:
                return None
            
            async with semaphore:
                try:
                    start_time = time.time()
                    
                    # 根据端口决定是否使用SSL
                    if port == 443:
                        # HTTPS端口使用SSL
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        
                        reader, writer = await asyncio.wait_for(
                            asyncio.open_connection(ip, port, ssl=ssl_context),
                            timeout=timeout
                        )
                    else:
                        # HTTP端口不使用SSL
                        reader, writer = await asyncio.wait_for(
                            asyncio.open_connection(ip, port),
                            timeout=timeout
                        )
                    
                    latency = (time.time() - start_time) * 1000
                    writer.close()
                    await writer.wait_closed()
                    
                    return IPResult(ip=ip, port=port, latency=latency, success=True)
                    
                except Exception as e:
                    return IPResult(ip=ip, port=port, latency=float('inf'), success=False, error=str(e))
        
        # 创建任务
        tasks = []
        for i, ip in enumerate(ips):
            if not self.is_running:
                break
            task = asyncio.create_task(test_single_ip(ip))
            tasks.append(task)
            
            if (i + 1) % 50 == 0:
                logger.info(f"已创建 {i + 1}/{len(ips)} 个测试任务")
        
        logger.info(f"已创建 {len(tasks)}/{len(ips)} 个测试任务")
        logger.info("正在执行延迟测试...")
        
        # 执行任务
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for result in completed_results:
            if isinstance(result, IPResult) and result.success:
                results.append(result)
        
        logger.info(f"测试完成，成功: {len(results)}/{len(ips)}")
        return results
    
    async def upload_ips(self, results: List[IPResult]):
        """上传IP到KV存储"""
        if not results:
            logger.error("没有可上传的IP")
            return
        
        # 生成IP列表文本，格式：IP:端口#延迟ms
        ip_list = '\n'.join([f"{result.ip}:{result.port}#{result.latency:.2f}ms" for result in results])
        
        logger.info(f"正在上传 {len(results)} 个IP到KV空间，操作: {self.operation_var.get()}")
        
        try:
            # Worker API请求头
            headers = {
                'X-API-Key': self.config['worker_api_key'],
                'Content-Type': 'application/json'
            }
            
            # 使用Worker API上传
            upload_data = {
                'ips': [f"{result.ip}:{result.port}#{result.latency:.2f}ms" for result in results],
                'action': self.operation_var.get(),
                'key': 'ADD.txt'
            }
            
            async with aiohttp.ClientSession() as session:
                api_url = f"{self.config['worker_url'].rstrip('/')}/api/ips"
                async with session.post(api_url, headers=headers, json=upload_data) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        if result_data.get('success'):
                            logger.info(f"上传成功: {result_data.get('message', '成功保存IP')}")
                        else:
                            logger.error(f"上传失败: {result_data.get('error', '未知错误')}")
                    else:
                        error_text = await response.text()
                        logger.error(f"上传失败: HTTP {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"上传IP到KV失败: {e}")

def main():
    """主函数"""
    root = tk.Tk()
    app = CloudflareIPOptimizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()