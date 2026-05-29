# -*- coding: utf-8 -*-
"""
洛谷工具 - 命令行前端
======================
交互式菜单界面，直接调用后端引擎函数（无子进程通信，更安全）。
"""

import os
import sys
import re
import time
import getpass

# 直接将 Server.py 作为模块导入（消除子进程，避免密码在进程列表中泄露）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Server import (
    login,
    view_page,
    get_profile,
    get_home,
    clear_cookie,
    is_logged_in,
)

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
        CYAN = ""
        MAGENTA = ""
    class Style:
        BRIGHT = ""
        RESET_ALL = ""


# ==============================================
# 全局配置
# ==============================================
class Config:
    URL_REGEX = re.compile(r'^https?://.+$')
    MENU = {
        "1": ("登录洛谷", "login"),
        "2": ("访问页面", "view"),
        "3": ("查看用户资料", "profile"),
        "4": ("查看主页运势/动态", "home"),
        "5": ("退出登录(清除Cookie)", "logout"),
        "0": ("退出程序", "exit"),
    }


# ==============================================
# 基础工具函数
# ==============================================

def print_header(title: str) -> None:
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}{Style.RESET_ALL}")

def print_success(msg: str) -> None:
    print(f"{Fore.GREEN}[✓] {msg}{Style.RESET_ALL}")

def print_error(msg: str) -> None:
    print(f"{Fore.RED}[×] {msg}{Style.RESET_ALL}")

def print_warning(msg: str) -> None:
    print(f"{Fore.YELLOW}[!] {msg}{Style.RESET_ALL}")

def print_info(msg: str) -> None:
    print(f"{Fore.BLUE}[ℹ] {msg}{Style.RESET_ALL}")

def print_field(label: str, value: str, indent: int = 2) -> None:
    """格式化输出字段"""
    prefix = " " * indent
    print(f"{prefix}{Fore.CYAN}{label}:{Style.RESET_ALL} {value}")

def print_section(title: str) -> None:
    print(f"\n{Fore.MAGENTA}── {title} ──{Style.RESET_ALL}")

def print_divider() -> None:
    print(f"{Fore.BLUE}{'-'*40}{Style.RESET_ALL}")


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
        if not re.match(r'^https?://.+$', value.strip()):
            print_error("URL 必须以 http/https 开头")
            return False
        return True
    return True


# ==============================================
# 业务功能实现
# ==============================================

def do_login() -> None:
    """登录洛谷（安全密码输入）"""
    print_header("洛谷账号登录")

    # 输入用户名
    while True:
        username = input("用户名/邮箱：").strip()
        if validate_input(username, "user"):
            break

    # 输入密码（使用 getpass 隐藏输入，不在命令行参数中传递）
    while True:
        password = getpass.getpass("密码（输入隐藏）：").strip()
        if validate_input(password, "pwd"):
            break

    # 直接调用后端函数（无需子进程）
    print_info("正在登录，请稍候...")
    result = login(username, password)

    # 清除内存中的密码
    password = ""

    if result["code"] == 200:
        print_success("登录成功，Cookie 已本地保存")
    elif result["code"] == 400:
        print_error(f"登录失败：{result['msg']}")
    else:
        print_error(f"系统错误：{result['msg']}")


def do_view() -> None:
    """访问洛谷页面"""
    print_header("访问洛谷页面")

    url = ""
    while True:
        url = input("访问 URL（留空用默认）：").strip()
        if validate_input(url, "url"):
            break

    result = view_page(url if url else None)

    if result["code"] == 200:
        print_success(f"访问成功：{result['url']}")
        print_info(f"页面大小：{len(result['html'])} 字符")

        if input("\n是否保存页面源码到文件？(y/n)：").strip().lower() == "y":
            filename = f"page_{int(time.time())}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(result["html"])
            print_success(f"源码已保存到：{filename}")

    elif result["code"] == 401:
        print_warning("未登录，请先执行登录操作")
    else:
        print_error(f"访问失败：{result['msg']}")


def do_profile() -> None:
    """查看用户资料"""
    print_header("用户资料")

    url = input("用户主页 URL（留空用默认）：").strip()

    result = get_profile(url if url else None)

    if result["code"] == 200:
        print_success("获取用户资料成功\n")
        data = result["data"]

        # 1) 统计数据（关注/粉丝/提交/通过/排名/等级分）
        if "stats" in data and data["stats"]:
            print_section("统计数据")
            for name, value in data["stats"].items():
                print_field(name, value)

        # 2) 基本信息
        if "basic_info" in data and data["basic_info"]:
            print_section("基本信息")
            for label, info in data["basic_info"].items():
                print_field(label, info.get("text", ""))
                if info.get("href"):
                    print_field("  链接", f"https://www.luogu.com.cn{info['href']}")

        # 3) 咕值
        if "guzhi" in data and data["guzhi"]:
            print_section("咕值")
            for label, info in data["guzhi"].items():
                print_field(label, info.get("text", ""))
                if info.get("href"):
                    print_field("  链接", f"https://www.luogu.com.cn{info['href']}")

        # 4) 比赛等级分
        if "contest_rating" in data and data["contest_rating"]:
            print_section("比赛等级分")
            for label, info in data["contest_rating"].items():
                print_field(label, info.get("text", ""))
                if info.get("href"):
                    print_field("  链接", f"https://www.luogu.com.cn{info['href']}")

        print()

    elif result["code"] == 401:
        print_warning("未登录，请先执行登录操作")
    else:
        print_error(f"获取失败：{result['msg']}")


def do_home() -> None:
    """查看主页运势/动态"""
    print_header("洛谷主页")

    result = get_home()

    if result["code"] == 200:
        data = result["data"]

        # 用户名
        if "username" in data:
            print_success(f"用户：{data['username']}")

        # 打卡天数
        if "checkin_days" in data:
            print_field("连续打卡", f"{data['checkin_days']} 天")

        # 运势
        if "fortune" in data:
            fortune = data["fortune"]
            print_section("今日运势")
            if "result" in fortune:
                print_field("运势", fortune["result"], indent=4)
            if "do" in fortune:
                for item in fortune["do"]:
                    print_field("宜", f"{item['activity']} —— {item['detail']}", indent=4)
            if "dont" in fortune:
                for item in fortune["dont"]:
                    print_field("忌", f"{item['activity']} —— {item['detail']}", indent=4)

        # 动态
        if "feed" in data and data["feed"]:
            print_section("最新动态")
            for i, item in enumerate(data["feed"][:10], 1):  # 最多显示 10 条
                print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                      f"{Fore.GREEN}{item['username']}{Style.RESET_ALL} "
                      f"({item['time']})")
                print(f"    {item['content'][:80]}{'...' if len(item['content']) > 80 else ''}")

        if not data:
            print_warning("未解析到数据，可能页面结构已变化")
        print()

    elif result["code"] == 401:
        print_warning("未登录，请先执行登录操作")
    else:
        print_error(f"获取失败：{result['msg']}")


def do_logout() -> None:
    """退出登录（清除 Cookie）"""
    print_header("退出登录")

    if not is_logged_in():
        print_info("当前未登录")
        return

    confirm = input("确定要清除登录状态吗？(y/n)：").strip().lower()
    if confirm == "y":
        result = clear_cookie()
        if result["status"]:
            print_success("已退出登录，Cookie 已清除")
        else:
            print_error(result["msg"])
    else:
        print_info("已取消")


# ==============================================
# 主程序入口
# ==============================================

def main():
    print(f"\n{Style.BRIGHT}{Fore.CYAN}╔{'═'*40}╗")
    print(f"║{' ' * 12}洛谷命令行工具{' ' * 13}║")
    print(f"╚{'═'*40}╝{Style.RESET_ALL}")

    # 检查登录状态
    if is_logged_in():
        print_success("检测到已保存的登录状态\n")
    else:
        print_info("当前未登录，请先执行登录操作\n")

    while True:
        # 打印菜单
        print(f"{Fore.BLUE}{'─'*40}{Style.RESET_ALL}")
        for k, (name, _) in Config.MENU.items():
            print(f"  {Fore.YELLOW}{k}{Style.RESET_ALL}. {name}")
        print(f"{Fore.BLUE}{'─'*40}{Style.RESET_ALL}")

        choice = input(f"\n{Fore.CYAN}输入选项：{Style.RESET_ALL}").strip()
        if choice not in Config.MENU:
            print_error("无效选项，请重新输入")
            continue

        _, func_name = Config.MENU[choice]

        if func_name == "exit":
            print_info("程序退出，再见！")
            break
        elif func_name == "login":
            do_login()
        elif func_name == "view":
            do_view()
        elif func_name == "profile":
            do_profile()
        elif func_name == "home":
            do_home()
        elif func_name == "logout":
            do_logout()


if __name__ == "__main__":
    main()
