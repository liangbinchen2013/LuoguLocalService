# -*- coding: utf-8 -*-
"""
洛谷工具 - 命令行前端
======================
CMD 风格命令行界面，直接调用后端引擎函数。
输入 help 查看命令列表。
"""

import os
import sys
import re
import getpass

# 直接将 Server.py 作为模块导入（消除子进程，避免密码在进程列表中泄露）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Server import (
    login,
    get_profile,
    get_home,
    clear_cookie,
    is_logged_in,
    view_feed,
    load_more_feed,
    view_problem,
    view_discuss,
    view_article,
)

# Rich 终端 Markdown 渲染
try:
    from rich.console import Console
    from rich.markdown import Markdown
    _console = Console()
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

# 终端颜色支持（colorama 降级方案）
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = RED = YELLOW = BLUE = CYAN = MAGENTA = ""
    class Style:
        BRIGHT = RESET_ALL = ""


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
    prefix = " " * indent
    print(f"{prefix}{Fore.CYAN}{label}:{Style.RESET_ALL} {value}")

def print_section(title: str) -> None:
    print(f"\n{Fore.MAGENTA}── {title} ──{Style.RESET_ALL}")

def print_divider() -> None:
    print(f"{Fore.BLUE}{'-'*40}{Style.RESET_ALL}")


# ==============================================
# Markdown 渲染
# ==============================================

def _simplify_latex(text: str) -> str:
    """简化 LaTeX 数学公式为纯文本"""
    text = re.sub(r'\$\$.*?\$\$', '[数学公式]', text, flags=re.DOTALL)
    text = re.sub(r'\$([^$]+?)\$', lambda m: m.group(1).strip(), text)
    return text


def _render_markdown(title: str, markdown_text: str) -> None:
    """用 rich 渲染 Markdown（不可用时降级为纯文本）"""
    if not markdown_text or not markdown_text.strip():
        print_info(f"{title}：无内容")
        return

    cleaned = _simplify_latex(markdown_text)

    if _HAS_RICH:
        print_section(title)
        try:
            md = Markdown(cleaned)
            _console.print(md)
            print()
            return
        except Exception:
            pass

    # 降级方案
    print_section(title)
    print(f"  {cleaned[:2000]}")
    if len(cleaned) > 2000:
        print(f"  {Fore.YELLOW}... (内容过长，共 {len(cleaned)} 字符){Style.RESET_ALL}")
    print()


# ==============================================
# 命令处理函数
# ==============================================

def cmd_login(args: list[str]) -> None:
    """登录洛谷"""
    print_header("洛谷账号登录")
    while True:
        username = input("用户名/邮箱：").strip()
        if username.strip():
            break
        print_error("用户名不能为空")
    while True:
        password = getpass.getpass("密码（输入隐藏）：").strip()
        if password:
            break
        print_error("密码不能为空")

    print_info("正在登录，请稍候...")
    result = login(username, password)
    password = ""  # 清除内存中的密码

    if result["code"] == 200:
        print_success("登录成功，Cookie 已本地保存")
    elif result["code"] == 400:
        print_error(f"登录失败：{result['msg']}")
    else:
        print_error(f"系统错误：{result['msg']}")


def cmd_profile(args: list[str]) -> None:
    """查看用户资料"""
    uid = args[0] if args else ""
    if not uid:
        uid = input("用户 UID（留空用默认）：").strip()
    url = f"https://www.luogu.com.cn/user/{uid}" if uid else None

    print_header("用户资料")
    result = get_profile(url)

    if result["code"] == 200:
        print_success("获取用户资料成功\n")
        data = result["data"]

        if "stats" in data and data["stats"]:
            print_section("统计数据")
            for name, value in data["stats"].items():
                print_field(name, value)

        if "basic_info" in data and data["basic_info"]:
            print_section("基本信息")
            for label, info in data["basic_info"].items():
                print_field(label, info.get("text", ""))
                if info.get("href"):
                    print_field("  链接", f"https://www.luogu.com.cn{info['href']}")

        if "guzhi" in data and data["guzhi"]:
            print_section("咕值")
            for label, info in data["guzhi"].items():
                print_field(label, info.get("text", ""))
                if info.get("href"):
                    print_field("  链接", f"https://www.luogu.com.cn{info['href']}")

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


def cmd_home(args: list[str]) -> None:
    """查看主页运势/动态"""
    print_header("洛谷主页")
    result = get_home()

    if result["code"] == 200:
        data = result["data"]
        if "username" in data:
            print_success(f"用户：{data['username']}")
        if "checkin_days" in data:
            print_field("连续打卡", f"{data['checkin_days']} 天")
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
        if "feed" in data and data["feed"]:
            print_section("最新动态")
            for i, item in enumerate(data["feed"][:10], 1):
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


def cmd_feed(args: list[str]) -> None:
    """查看犇犇动态（分页加载）"""
    print_header("犇犇动态")
    loaded_items = []
    page = 0

    while True:
        print_info(f"正在获取第 {page * 10 + 1}-{(page + 1) * 10} 条犇犇...")
        result = view_feed() if page == 0 else load_more_feed(page)

        if result["code"] == 401:
            print_warning("未登录，请先执行登录操作")
            return
        elif result["code"] != 200:
            print_error(f"获取失败：{result['msg']}")
            return

        items = result["data"]["items"]
        if not items:
            if page == 0:
                print_warning("未获取到犇犇动态")
            else:
                print_info("没有更多犇犇了")
            break

        loaded_items.extend(items)
        start = len(loaded_items) - len(items) + 1
        for i, item in enumerate(items, start):
            # 打印单条犇犇（无 post_id 链接）
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                  f"{Fore.GREEN}{item['username']}{Style.RESET_ALL} "
                  f"({item.get('uid', '?')})  "
                  f"{Fore.BLUE}{item.get('time', '')}{Style.RESET_ALL}")
            content = item.get("content", "")
            for line in content.split("\n"):
                print(f"      {line}")
        print()

        has_more = result["data"].get("has_more", False) and len(items) >= 10
        if not has_more:
            print_success(f"共加载 {len(loaded_items)} 条犇犇（已全部加载）")
            break

        choice = input(f"{Fore.CYAN}输入 y 加载下一页，按回车结束：{Style.RESET_ALL}").strip().lower()
        if choice != "y":
            print_success(f"共加载 {len(loaded_items)} 条犇犇")
            break
        page += 1


def cmd_problem(args: list[str]) -> None:
    """查看题目预览"""
    if not args:
        print_error("用法: problem <题目ID>  例如: problem P1000")
        return

    pid = args[0].upper()
    print_header(f"题目预览：{pid}")
    print_info("正在获取题目...")
    result = view_problem(pid)

    if result["code"] == 401:
        print_warning("未登录，请先执行登录操作")
        return
    elif result["code"] != 200:
        print_error(f"获取失败：{result['msg']}")
        return

    data = result["data"]
    content = data.get("content", {})

    # 标题行
    print(f"\n  {Fore.CYAN}{Style.BRIGHT}{data.get('pid', pid)}{Style.RESET_ALL}  "
          f"{Fore.GREEN}{data.get('name', '')}{Style.RESET_ALL}")
    print(f"  难度: {data['difficulty']}  |  "
          f"提交: {data.get('totalSubmit', 0):,}  |  "
          f"通过: {data.get('totalAccepted', 0):,}")
    if data.get("provider"):
        print(f"  提供者: {data['provider']}")
    print()

    # 各章节（使用 rich 渲染 Markdown）
    sections = [
        ("题目背景", "background"),
        ("题目描述", "description"),
        ("输入格式", "formatI"),
        ("输出格式", "formatO"),
    ]
    for sec_title, key in sections:
        text = content.get(key, "").strip()
        if text:
            _render_markdown(sec_title, text)

    # 输入输出样例
    samples = data.get("samples", [])
    if samples:
        print_section("输入输出样例")
        for i, (inp, out) in enumerate(samples, 1):
            if inp or out:
                print(f"  {Fore.YELLOW}样例 #{i}{Style.RESET_ALL}")
                if inp:
                    print(f"    {Fore.CYAN}输入:{Style.RESET_ALL}")
                    for line in inp.strip().split("\n"):
                        print(f"      {line}")
                if out:
                    print(f"    {Fore.CYAN}输出:{Style.RESET_ALL}")
                    for line in out.strip().split("\n"):
                        print(f"      {line}")
                print()

    # 说明/提示
    hint = content.get("hint", "").strip()
    if hint:
        _render_markdown("说明/提示", hint)


def cmd_discuss(args: list[str]) -> None:
    """查看讨论帖"""
    if not args:
        print_error("用法: discuss <讨论ID>  例如: discuss 962230")
        return

    did = args[0]
    print_header(f"讨论帖：{did}")
    print_info("正在获取讨论...")
    result = view_discuss(did)

    if result["code"] == 401:
        print_warning("未登录，请先执行登录操作")
        return
    elif result["code"] != 200:
        print_error(f"获取失败：{result['msg']}")
        return

    d = result["data"]
    print(f"\n  {Fore.CYAN}{Style.BRIGHT}{d['title']}{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}{d['author']}{Style.RESET_ALL}  "
          f"|  {d['time']}  |  {Fore.YELLOW}{d['forum']}{Style.RESET_ALL}  "
          f"|  {d['replyCount']} 条回复")
    print()

    _render_markdown("讨论内容", d.get("content", ""))


def cmd_article(args: list[str]) -> None:
    """查看文章"""
    if not args:
        print_error("用法: article <文章ID>  例如: article qzywo77y")
        return

    aid = args[0]
    print_header(f"文章：{aid}")
    print_info("正在获取文章...")
    result = view_article(aid)

    if result["code"] == 401:
        print_warning("未登录，请先执行登录操作")
        return
    elif result["code"] != 200:
        print_error(f"获取失败：{result['msg']}")
        return

    d = result["data"]
    print(f"\n  {Fore.CYAN}{Style.BRIGHT}{d['title']}{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}{d['author']}{Style.RESET_ALL}  "
          f"|  {d['time']}  |  {Fore.YELLOW}{d['category']}{Style.RESET_ALL}")
    print(f"  赞 {d['upvote']}  |  回复 {d['replyCount']}  |  收藏 {d['favorCount']}")
    print()

    _render_markdown("文章内容", d.get("content", ""))


def cmd_logout(args: list[str]) -> None:
    """退出登录"""
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


def cmd_help(args: list[str]) -> None:
    """显示帮助信息"""
    print_header("洛谷命令行工具 - 帮助")
    print(f"  {Fore.YELLOW}命令{Style.RESET_ALL}              {Fore.CYAN}说明{Style.RESET_ALL}")
    print(f"  {Fore.BLUE}{'-'*50}{Style.RESET_ALL}")
    for cmd, (desc, _) in sorted(COMMANDS.items()):
        print(f"  {Fore.GREEN}{cmd:<16}{Style.RESET_ALL} {desc}")
    print()
    print(f"  {Fore.YELLOW}提示:{Style.RESET_ALL} 输入命令后跟参数，例如: profile 1432496")
    print(f"  {Fore.YELLOW}提示:{Style.RESET_ALL} 输入 profile 可不带参数，交互式输入 UID")
    print()


def cmd_exit(args: list[str]) -> None:
    """退出程序"""
    print_info("程序退出，再见！")
    sys.exit(0)


# ==============================================
# 命令调度
# ==============================================

COMMANDS: dict[str, tuple[str, callable]] = {
    "login":    ("登录洛谷", cmd_login),
    "profile":  ("查看用户资料 [UID]", cmd_profile),
    "home":     ("查看主页运势/动态", cmd_home),
    "feed":     ("查看犇犇动态", cmd_feed),
    "problem":  ("查看题目预览 <PID>", cmd_problem),
    "discuss":  ("查看讨论帖 <ID>", cmd_discuss),
    "article":  ("查看文章 <ID>", cmd_article),
    "logout":   ("退出登录(清除Cookie)", cmd_logout),
    "help":     ("显示帮助信息", cmd_help),
    "exit":     ("退出程序", cmd_exit),
    "quit":     ("退出程序", cmd_exit),
}

ALIASES = {
    "cls": "help",
    "clear": "help",
    "？": "help",
    "h": "help",
    "q": "exit",
    "quit": "exit",
    "user": "profile",
    "p": "problem",
    "d": "discuss",
    "dis": "discuss",
    "a": "article",
    "art": "article",
}


def main():
    print(f"\n{Style.BRIGHT}{Fore.CYAN}╔{'═'*40}╗")
    print(f"║{' ' * 12}洛谷命令行工具{' ' * 13}║")
    print(f"╚{'═'*40}╝{Style.RESET_ALL}")

    if is_logged_in():
        print_success("检测到已保存的登录状态\n")
    else:
        print_info("当前未登录，请先执行 login\n")

    while True:
        try:
            raw = input(f"{Fore.CYAN}luogu>{Style.RESET_ALL} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            cmd_exit([])

        if not raw:
            continue

        parts = raw.split()
        cmd_name = parts[0].lower()
        cmd_args = parts[1:]

        # 别名解析
        resolved = ALIASES.get(cmd_name, cmd_name)

        if resolved in COMMANDS:
            _, handler = COMMANDS[resolved]
            try:
                handler(cmd_args)
            except Exception as e:
                print_error(f"命令执行出错：{e}")
        else:
            print_error(f"未知命令: {cmd_name}，输入 help 查看可用命令")


if __name__ == "__main__":
    main()
