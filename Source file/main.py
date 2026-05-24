import subprocess
import json
import os
import sys
import re
import getpass
import time
from typing import Optional

# 终端颜色支持（可选，未安装自动降级）
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = ""
        RED = ""
        YELLOW = ""
        BLUE = ""
    class Style:
        BRIGHT = ""
        RESET_ALL = ""

# ==============================================
# 全局配置
# ==============================================
class Config:
    SERVER_PATH = os.path.join(os.path.dirname(__file__), "Server.py")
    URL_REGEX = re.compile(r'^https?://.+$')
    MENU = {
        "1": ("登录洛谷", "login"),
        "2": ("访问页面", "view"),
        "0": ("退出", "exit")
    }

# ==============================================
# 基础工具函数
# ==============================================
def print_success(msg: str) -> None:
    print(f"{Fore.GREEN}[✓] {msg}{Style.RESET_ALL}")

def print_error(msg: str) -> None:
    print(f"{Fore.RED}[×] {msg}{Style.RESET_ALL}")

def print_warning(msg: str) -> None:
    print(f"{Fore.YELLOW}[!] {msg}{Style.RESET_ALL}")

def print_info(msg: str) -> None:
    print(f"{Fore.BLUE}[ℹ] {msg}{Style.RESET_ALL}")

def validate_input(value: str, type_: str) -> bool:
    """输入校验：user/pwd/url"""
    if type_ in ("user", "pwd"):
        if not value.strip():
            print_error(f"{type_ == 'user' and '用户名' or '密码'}不能为空")
            return False
        return True
    elif type_ == "url":
        if not value.strip():
            return True  
        if not Config.URL_REGEX.match(value.strip()):
            print_error("URL必须以http/https开头")
            return False
        return True
    return True

def call_server(args: list) -> Optional[dict]:
    """统一调用后端Server.py，返回解析后的JSON"""
    try:
        cmd = [sys.executable, Config.SERVER_PATH] + args
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            timeout=30
        )

        if result.stderr:
            print_error(f"后端错误：{result.stderr.strip()}")
            return None

        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        print_error("请求超时(30秒)")
    except json.JSONDecodeError:
        print_error(f"后端返回格式错误：{result.stdout.strip()}")
    except Exception as e:
        print_error(f"执行失败：{str(e)}")
    return None

# ==============================================
# 业务功能实现
# ==============================================
def do_login() -> None:
    """登录功能"""
    print_info("\n=== 洛谷账号登录 ===")
    
    # 输入用户名
    while True:
        username = input("用户名/邮箱：").strip()
        if validate_input(username, "user"):
            break
    
    # 输入密码（隐藏）
    while True:
        password = getpass.getpass("密码（输入隐藏）：").strip()
        if validate_input(password, "pwd"):
            break
    
    # 调用后端
    res = call_server(["login", "--user", username, "--pwd", password])
    if not res:
        return
    
    if res["code"] == 200:
        print_success("登录成功，Cookie已本地保存")
    elif res["code"] == 400:
        print_error(f"登录失败：{res['msg']}")
    else:
        print_error(f"系统错误：{res['msg']}")

def do_view() -> None:
    """页面访问功能"""
    print_info("\n=== 访问洛谷页面 ===")
    
    # 输入URL
    while True:
        url = input("访问URL（留空用默认）：").strip()
        if validate_input(url, "url"):
            break
    
    # 构造命令
    cmd_args = ["view"]
    if url:
        cmd_args.extend(["--url", url])
    
    # 调用后端
    res = call_server(cmd_args)
    if not res:
        return
    
    if res["code"] == 200:
        print_success(f"访问成功：{res['url']}")
        # 可选：保存页面源码到文件
        if input("是否保存页面源码？(y/n)：").strip().lower() == "y":
            filename = f"page_{int(time.time())}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(res["html"])
            print_success(f"源码已保存到：{filename}")
    elif res["code"] == 401:
        print_warning("未登录，请先执行登录操作")
    else:
        print_error(f"访问失败：{res['msg']}")

# ==============================================
# 主程序入口
# ==============================================
def main():
    print(f"{Style.BRIGHT}洛谷工具 - 命令行前端{Style.RESET_ALL}")
    print("=" * 30)
    
    while True:
        # 打印菜单
        print("\n请选择功能：")
        for k, (name, _) in Config.MENU.items():
            print(f"  {k}. {name}")
        
        # 读取用户选择
        choice = input("\n输入选项：").strip()
        if choice not in Config.MENU:
            print_error("无效选项，请重新输入")
            continue
        
        # 执行对应功能
        _, func_name = Config.MENU[choice]
        if func_name == "exit":
            print_info("程序退出")
            break
        elif func_name == "login":
            do_login()
        elif func_name == "view":
            do_view()

if __name__ == "__main__":
    # 补全缺失的time导入（保存文件用）
    main()