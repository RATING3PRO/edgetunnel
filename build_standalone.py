#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本
用于将独立GUI程序打包为单个exe文件
"""

import PyInstaller.__main__
import os
import sys

def build_exe():
    """构建exe文件"""
    
    # 获取当前脚本目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 源文件路径
    source_file = os.path.join(current_dir, 'ip_optimizer_standalone.py')
    
    # 输出目录
    dist_dir = os.path.join(current_dir, 'dist')
    build_dir = os.path.join(current_dir, 'build')
    
    # PyInstaller参数
    args = [
        '--onefile',  # 打包为单个文件
        '--windowed',  # Windows下不显示控制台窗口
        '--name=CloudflareIPOptimizer',  # 可执行文件名称
        '--distpath=' + dist_dir,  # 输出目录
        '--workpath=' + build_dir,  # 临时文件目录
        '--clean',  # 清理临时文件
        '--noconfirm',  # 不询问覆盖
        # 添加图标（如果存在）
        # '--icon=icon.ico',
        # 隐藏导入警告
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.scrolledtext',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=asyncio',
        '--hidden-import=aiohttp',
        '--hidden-import=ssl',
        '--hidden-import=socket',
        '--hidden-import=ipaddress',
        '--hidden-import=concurrent.futures',
        '--hidden-import=threading',
        '--hidden-import=logging',
        '--hidden-import=json',
        '--hidden-import=time',
        '--hidden-import=datetime',
        '--hidden-import=dataclasses',
        '--hidden-import=typing',
        source_file
    ]
    
    print("开始打包独立GUI程序...")
    print(f"源文件: {source_file}")
    print(f"输出目录: {dist_dir}")
    
    try:
        # 运行PyInstaller
        PyInstaller.__main__.run(args)
        
        # 检查输出文件
        exe_file = os.path.join(dist_dir, 'CloudflareIPOptimizer.exe')
        if os.path.exists(exe_file):
            file_size = os.path.getsize(exe_file) / (1024 * 1024)  # MB
            print(f"\n打包成功！")
            print(f"输出文件: {exe_file}")
            print(f"文件大小: {file_size:.1f} MB")
            print(f"\n可以直接运行 {exe_file}")
        else:
            print("打包失败：未找到输出文件")
            return False
            
    except Exception as e:
        print(f"打包过程出错: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # 检查PyInstaller是否已安装
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("未安装PyInstaller，请先安装:")
        print("pip install pyinstaller")
        sys.exit(1)
    
    # 检查源文件是否存在
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_file = os.path.join(current_dir, 'ip_optimizer_standalone.py')
    
    if not os.path.exists(source_file):
        print(f"源文件不存在: {source_file}")
        sys.exit(1)
    
    # 开始打包
    success = build_exe()
    
    if success:
        print("\n打包完成！")
        input("按回车键退出...")
    else:
        print("\n打包失败！")
        input("按回车键退出...")
        sys.exit(1)