#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare IP优选器 - 独立GUI版本
内置配置参数，可打包为单个exe文件
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
import os
import sys

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

class ConfigDialog:
    """配置对话框"""
    
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config.copy()
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("配置设置")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        
    def create_widgets(self):
        """创建配置界面组件"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Worker URL
        ttk.Label(main_frame, text="Worker URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.worker_url_var = tk.StringVar(value=self.config.get('worker_url', ''))
        worker_url_entry = ttk.Entry(main_frame, textvariable=self.worker_url_var, width=50)
        worker_url_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # API Key
        ttk.Label(main_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar(value=self.config.get('worker_api_key', ''))
        api_key_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, width=50, show="*")
        api_key_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # 超时时间
        ttk.Label(main_frame, text="超时时间(秒):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.StringVar(value=str(self.config.get('timeout', 3)))
        timeout_entry = ttk.Entry(main_frame, textvariable=self.timeout_var, width=20)
        timeout_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 最大并发数
        ttk.Label(main_frame, text="最大并发数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.max_workers_var = tk.StringVar(value=str(self.config.get('max_workers', 50)))
        max_workers_entry = ttk.Entry(main_frame, textvariable=self.max_workers_var, width=20)
        max_workers_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 测试次数
        ttk.Label(main_frame, text="测试次数:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.test_count_var = tk.StringVar(value=str(self.config.get('test_count', 3)))
        test_count_entry = ttk.Entry(main_frame, textvariable=self.test_count_var, width=20)
        test_count_entry.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 保存IP数量
        ttk.Label(main_frame, text="保存IP数量:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.best_count_var = tk.StringVar(value=str(self.config.get('best_count', 16)))
        best_count_entry = ttk.Entry(main_frame, textvariable=self.best_count_var, width=20)
        best_count_entry.grid(row=5, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # 说明文本
        info_frame = ttk.LabelFrame(main_frame, text="说明", padding="10")
        info_frame.grid(row=7, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        info_text = (
            "• Worker URL: 您的Cloudflare Worker部署地址\n"
            "• API Key: 在Worker环境变量中设置的API密钥\n"
            "• 超时时间: 单次IP测试的超时时间\n"
            "• 最大并发数: 同时测试的IP数量\n"
            "• 测试次数: 每个IP的测试次数\n"
            "• 保存IP数量: 保存到KV的最优IP数量"
        )
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack()
        
    def save_config(self):
        """保存配置"""
        try:
            self.config['worker_url'] = self.worker_url_var.get().strip()
            self.config['worker_api_key'] = self.api_key_var.get().strip()
            self.config['timeout'] = int(self.timeout_var.get())
            self.config['max_workers'] = int(self.max_workers_var.get())
            self.config['test_count'] = int(self.test_count_var.get())
            self.config['best_count'] = int(self.best_count_var.get())
            
            if not self.config['worker_url']:
                messagebox.showerror("错误", "Worker URL不能为空")
                return
            if not self.config['worker_api_key']:
                messagebox.showerror("错误", "API Key不能为空")
                return
                
            self.result = self.config
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def cancel(self):
        """取消配置"""
        self.dialog.destroy()

class CloudflareIPOptimizerStandalone:
    """Cloudflare IP优选器独立GUI类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Cloudflare IP优选器 v2.0")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        
        # 设置图标（如果存在）
        try:
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller打包后的路径
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                icon_path = 'icon.ico'
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # 默认配置
        self.config = {
            'worker_url': '',
            'worker_api_key': '',
            'timeout': 3,
            'max_workers': 50,
            'test_count': 3,
            'best_count': 16,
            'default_ip_source': 'official',
            'default_port': 443,
            'default_action': 'replace'
        }
        
        # GUI变量
        self.port_var = tk.StringVar(value="443")
        self.source_var = tk.StringVar(value="official")
        self.action_var = tk.StringVar(value="replace")
        self.ip_count_var = tk.StringVar(value="0")  # 0表示不限制
        self.custom_ips = []
        self.is_running = False
        self.current_task = None
        
        # 创建界面
        self.create_widgets()
        
        # 重定向日志到GUI
        self.setup_logging()
    
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
        
        # 标题和配置按钮
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=row, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
        title_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(title_frame, text="Cloudflare IP优选器 v2.0", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        config_button = ttk.Button(title_frame, text="配置设置", command=self.open_config_dialog)
        config_button.grid(row=0, column=1, sticky=tk.E)
        
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
        self.source_combo.set(self.ip_sources["official"])
        self.source_combo.bind('<<ComboboxSelected>>', self.on_source_changed)
        
        # 自定义IP按钮
        self.import_button = ttk.Button(source_frame, text="导入IP文件", command=self.import_ip_file)
        self.import_button.grid(row=0, column=1, padx=5)
        self.import_button.config(state='disabled')
        
        self.clear_button = ttk.Button(source_frame, text="清空自定义IP", command=self.clear_custom_ips)
        self.clear_button.grid(row=0, column=2, padx=5)
        self.clear_button.config(state='disabled')
        
        row += 1
        
        # 操作模式选择
        ttk.Label(main_frame, text="操作模式:").grid(row=row, column=0, sticky=tk.W, pady=5)
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Radiobutton(action_frame, text="替换模式", variable=self.action_var, value="replace").grid(row=0, column=0, padx=5)
        ttk.Radiobutton(action_frame, text="追加模式", variable=self.action_var, value="append").grid(row=0, column=1, padx=5)
        
        row += 1
        
        # IP数量限制
        ttk.Label(main_frame, text="IP数量限制:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ip_count_frame = ttk.Frame(main_frame)
        ip_count_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Entry(ip_count_frame, textvariable=self.ip_count_var, width=10).grid(row=0, column=0, padx=(0, 5))
        ttk.Label(ip_count_frame, text="个（0表示不限制）").grid(row=0, column=1, sticky=tk.W)
        
        row += 1
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="开始优选", command=self.start_optimization)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止优选", command=self.stop_optimization, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        row += 1
        
        # 进度条
        self.progress_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, text="状态:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        
        row += 1
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        row += 1
        
        # 日志显示
        ttk.Label(main_frame, text="运行日志:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=(10, 5))
        
        row += 1
        
        # 日志文本框
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def open_config_dialog(self):
        """打开配置对话框"""
        dialog = ConfigDialog(self.root, self.config)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.config = dialog.result
            self.log_message("配置已更新")
    
    def setup_logging(self):
        """设置日志重定向到GUI"""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                self.text_widget.after(0, append)
        
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_handler)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} - INFO - {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def import_ip_file(self):
        """导入IP文件"""
        file_path = filedialog.askopenfilename(
            title="选择IP文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                ips = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ips.append(line)
                
                self.custom_ips = ips
                self.log_message(f"已导入 {len(ips)} 个自定义IP")
            except Exception as e:
                messagebox.showerror("错误", f"导入文件失败: {e}")
    
    def clear_custom_ips(self):
        """清空自定义IP"""
        self.custom_ips = []
        self.log_message("已清空自定义IP列表")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def on_source_changed(self, event=None):
        """IP来源改变事件"""
        selected_text = self.source_combo.get()
        
        # 找到对应的键
        for key, value in self.ip_sources.items():
            if value == selected_text:
                self.source_var.set(key)
                break
        
        # 控制自定义IP按钮状态
        if self.source_var.get() == "custom":
            self.import_button.config(state='normal')
            self.clear_button.config(state='normal')
        else:
            self.import_button.config(state='disabled')
            self.clear_button.config(state='disabled')
    
    def start_optimization(self):
        """开始优选"""
        if not self.config.get('worker_url') or not self.config.get('worker_api_key'):
            messagebox.showerror("错误", "请先配置Worker URL和API Key")
            self.open_config_dialog()
            return
        
        if self.source_var.get() == "custom" and not self.custom_ips:
            messagebox.showerror("错误", "请先导入自定义IP文件")
            return
        
        self.is_running = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar.start()
        self.progress_var.set("正在运行...")
        
        # 在新线程中运行优选
        thread = threading.Thread(target=self.run_optimization)
        thread.daemon = True
        thread.start()
    
    def stop_optimization(self):
        """停止优选"""
        self.is_running = False
        if self.current_task:
            self.current_task.cancel()
        self.progress_var.set("正在停止...")
    
    def run_optimization(self):
        """运行优选（在新线程中）"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步优选
            self.current_task = loop.create_task(self.async_optimization())
            loop.run_until_complete(self.current_task)
            
        except asyncio.CancelledError:
            logger.info("优选已被用户取消")
        except Exception as e:
            logger.error(f"优选过程出错: {e}")
        finally:
            # 重置UI状态
            self.root.after(0, self.reset_ui_state)
    
    def reset_ui_state(self):
        """重置UI状态"""
        self.is_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar.stop()
        self.progress_var.set("就绪")
    
    async def async_optimization(self):
        """异步优选过程"""
        try:
            port = int(self.port_var.get())
            source = self.source_var.get()
            action = self.action_var.get()
            
            logger.info(f"开始IP优选 - 端口: {port}, 来源: {source}, 模式: {action}")
            
            # 获取IP列表
            self.progress_var.set("获取IP列表...")
            ips = await self.get_ip_list()
            
            if not ips:
                logger.error("未获取到IP列表")
                return
            
            logger.info(f"获取到 {len(ips)} 个IP地址")
            
            # 测试IP延迟
            self.progress_var.set("测试IP延迟...")
            results = await self.test_ips_latency(
                ips, port, 
                self.config['timeout'], 
                self.config['max_workers']
            )
            
            if not self.is_running:
                return
            
            # 筛选成功的结果
            successful_results = [r for r in results if r.success]
            
            if not successful_results:
                logger.error("没有找到可用的IP")
                return
            
            # 按延迟排序
            successful_results.sort(key=lambda x: x.latency)
            
            # 取最优的IP
            best_results = successful_results[:self.config['best_count']]
            
            logger.info(f"找到 {len(successful_results)} 个可用IP，选择最优的 {len(best_results)} 个")
            
            for i, result in enumerate(best_results[:5], 1):
                logger.info(f"Top {i}: {result.ip}:{result.port} - {result.latency:.2f}ms")
            
            # 上传结果
            self.progress_var.set("上传结果...")
            await self.upload_ips(best_results, action)
            
            logger.info("IP优选完成！")
            
        except Exception as e:
            logger.error(f"优选过程出错: {e}")
    
    async def get_ip_list(self) -> List[str]:
        """获取IP列表"""
        source = self.source_var.get()
        
        if source == "custom":
            return self.custom_ips
        
        # IP来源URL映射
        ip_sources = {
            "official": "https://www.cloudflare.com/ips-v4",
            "cm": "https://raw.githubusercontent.com/cmliu/cmliu/main/CF-CIDR.txt",
            "as13335": "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/13335/ipv4-aggregated.txt",
            "as209242": "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/209242/ipv4-aggregated.txt",
            "proxyip": "https://raw.githubusercontent.com/cmliu/ACL4SSR/main/baipiao.txt"
        }
        
        url = ip_sources.get(source)
        if not url:
            logger.error(f"未知的IP来源: {source}")
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # 解析IP列表
                        ips = []
                        for line in content.strip().split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # 处理CIDR格式
                                if '/' in line:
                                    try:
                                        network = ipaddress.ip_network(line, strict=False)
                                        # 从每个网段中选择一些IP
                                        hosts = list(network.hosts())
                                        if hosts:
                                            import random
                                            count = min(100, len(hosts))  # 每个网段最多100个
                                            selected_hosts = random.sample(hosts, count)
                                            ips.extend([str(ip) for ip in selected_hosts])
                                    except:
                                        continue
                                else:
                                    ips.append(line)
                        
                        # 去重并限制数量
                        ips = list(set(ips))
                        ip_limit = int(self.ip_count_var.get())
                        if ip_limit > 0 and len(ips) > ip_limit:
                            import random
                            ips = random.sample(ips, ip_limit)
                        
                        return ips
                    else:
                        logger.error(f"获取IP列表失败: HTTP {response.status}")
                        return []
        except Exception as e:
            logger.error(f"获取IP列表出错: {e}")
            return []
    
    async def test_ips_latency(self, ips: List[str], port: int, timeout: float, max_workers: int) -> List[IPResult]:
        """测试IP延迟"""
        results = []
        semaphore = asyncio.Semaphore(max_workers)
        
        async def test_single_ip(ip: str) -> IPResult:
            async with semaphore:
                if not self.is_running:
                    return IPResult(ip, port, -1, False, "已取消")
                
                try:
                    # 测试多次取平均值
                    latencies = []
                    for _ in range(self.config['test_count']):
                        if not self.is_running:
                            break
                        
                        start_time = time.time()
                        
                        try:
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
                            latencies.append(latency)
                            
                            writer.close()
                            await writer.wait_closed()
                            
                        except Exception:
                            continue
                    
                    if latencies:
                        avg_latency = sum(latencies) / len(latencies)
                        return IPResult(ip, port, avg_latency, True)
                    else:
                        return IPResult(ip, port, -1, False, "连接失败")
                        
                except Exception as e:
                    return IPResult(ip, port, -1, False, str(e))
        
        # 并发测试所有IP
        tasks = [test_single_ip(ip) for ip in ips]
        
        # 分批处理，避免内存占用过大
        batch_size = 1000
        for i in range(0, len(tasks), batch_size):
            if not self.is_running:
                break
            
            batch_tasks = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, IPResult):
                    results.append(result)
            
            # 更新进度
            progress = min(i + batch_size, len(tasks))
            self.progress_var.set(f"测试进度: {progress}/{len(tasks)}")
        
        return results
    
    async def upload_ips(self, results: List[IPResult], action: str = "replace"):
        """上传IP结果到KV"""
        try:
            # 准备IP列表，格式：IP:端口#延迟ms
            ip_list = [f"{result.ip}:{result.port}#{result.latency:.2f}ms" for result in results]
            
            # 准备请求数据
            data = {
                "ips": ip_list,
                "action": action,
                "key": "ADD.txt"
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.config['worker_api_key']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config['worker_url']}/api/ips",
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            logger.info(f"成功上传 {len(ip_list)} 个IP到KV空间")
                        else:
                            logger.error(f"上传失败: {result.get('error', '未知错误')}")
                    else:
                        error_text = await response.text()
                        logger.error(f"上传失败: HTTP {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"上传IP列表出错: {e}")

def main():
    """主函数"""
    root = tk.Tk()
    app = CloudflareIPOptimizerStandalone(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_running:
            if messagebox.askokcancel("退出", "优选正在运行，确定要退出吗？"):
                app.stop_optimization()
                root.after(1000, root.destroy)  # 延迟销毁窗口
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()