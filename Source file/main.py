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
import shutil

# LaTeX 转 Unicode 映射
from latex_unicode import latex_to_unicode

# 直接将 Server.py 作为模块导入（消除子进程，避免密码在进程列表中泄露）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Server import (
    VERSION,
    VERBOSE,
    login,
    get_profile,
    get_home,
    clear_cookie,
    is_logged_in,
    get_current_user,
    list_sessions,
    get_session_users,
    switch_session,
    view_feed,
    load_more_feed,
    view_problem,
    view_discuss,
    view_discuss_list,
    view_discuss_replies,
    view_article,
    view_article_list,
    view_article_replies,
    check_punch_status,
    do_punch,
    view_problem_list,
    view_judgement,
    load_user_notes,
    save_user_note,
    delete_user_note,
    get_user_note,
    load_user_colors,
    save_user_color,
    delete_user_color,
    get_user_color,
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
    print(f"{Fore.GREEN}[√] {msg}{Style.RESET_ALL}")

def print_error(msg: str) -> None:
    print(f"{Fore.RED}[×] {msg}{Style.RESET_ALL}")

def print_warning(msg: str) -> None:
    print(f"{Fore.YELLOW}[!] {msg}{Style.RESET_ALL}")

def print_info(msg: str) -> None:
    print(f"{Fore.BLUE}[i] {msg}{Style.RESET_ALL}")

def print_field(label: str, value: str, indent: int = 2) -> None:
    prefix = " " * indent
    print(f"{prefix}{Fore.CYAN}{label}:{Style.RESET_ALL} {value}")

def print_section(title: str) -> None:
    print(f"\n{Fore.MAGENTA}{'-'*4} {title} {'-'*4}{Style.RESET_ALL}")

def print_divider() -> None:
    print(f"{Fore.BLUE}{'-'*40}{Style.RESET_ALL}")


# ==============================================
# 用户颜色与备注
# ==============================================

# 洛谷颜色名 → colorama 颜色码
_LUOGU_COLOR_MAP = {
    "Red":       Fore.RED,
    "Purple":    Fore.MAGENTA,
    "Orange":    Fore.YELLOW,
    "Blue":      Fore.BLUE,
    "Green":     Fore.GREEN,
    "Cyan":      Fore.CYAN,
    "Gray":      Fore.LIGHTBLACK_EX if hasattr(Fore, 'LIGHTBLACK_EX') else Fore.RESET,
    "Brown":     "\033[38;5;130m",   # 深橙/棕
    "Gold":      "\033[38;5;220m",   # 金色
    "Cheater":   "\033[38;5;245m",   # 灰白
    "Black":     "\033[38;5;240m",   # 深灰
}


def _colorize(name: str, color: str, uid: str = "") -> str:
    """根据洛谷颜色名（优先自定义颜色）返回带ANSI颜色的用户名"""
    c = ""
    # 1. 用户自定义颜色优先
    if uid:
        custom = get_user_color(uid)
        if custom:
            c = _LUOGU_COLOR_MAP.get(custom) or custom
    # 2. 洛谷自带颜色
    if not c and color:
        c = _LUOGU_COLOR_MAP.get(color)
    if c:
        return f"{c}{name}{Style.RESET_ALL}"
    return f"{Fore.GREEN}{name}{Style.RESET_ALL}"


def _get_note_for(uid: str) -> str:
    """获取用户备注文本，用于显示"""
    n = get_user_note(uid)
    if n:
        return f" {Fore.MAGENTA}[{n}]{Style.RESET_ALL}"
    return ""


# ==============================================
# Markdown 渲染
# ==============================================

def _simplify_latex(text: str) -> str:
    """简化 LaTeX 数学公式为纯文本"""
    text = re.sub(r'\$\$.*?\$\$', '[数学公式]', text, flags=re.DOTALL)
    text = re.sub(r'\$([^$]+?)\$', lambda m: latex_to_unicode(m.group(1).strip()), text)
    return text


def _render_markdown(title: str, markdown_text: str) -> None:
    """渲染 Markdown，长内容按行分页（默认 30 行，空行也算）"""
    if not markdown_text or not markdown_text.strip():
        print_info(f"{title}：无内容")
        return

    cleaned = _simplify_latex(markdown_text)
    PAGE_LINES = 30
    lines = cleaned.split("\n")

    if len(lines) <= PAGE_LINES:
        _render_chunk(title, cleaned)
        return

    # 长内容：按行分页显示
    pos = 0
    page = 1
    while pos < len(lines):
        chunk = "\n".join(lines[pos:pos + PAGE_LINES])
        chunk_title = title if page == 1 else f"{title}（续）"
        _render_chunk(chunk_title, chunk)

        pos += PAGE_LINES
        if pos >= len(lines):
            break

        # 短提示，选择后清除行
        print(f"{Fore.YELLOW}[回车继续 | a全部 | q退出]{Style.RESET_ALL}", end="", flush=True)
        choice = input().strip().lower()
        print("\x1b[1A\x1b[K", end="", flush=True)  # 上移一行并清除
        if choice == 'q':
            break
        if choice == 'a':
            if pos < len(lines):
                _render_chunk(f"{title}（续）", "\n".join(lines[pos:]))
            break
        page += 1


def _render_chunk(title: str, text: str) -> None:
    """渲染单块内容（rich 优先，降级纯文本）"""
    if _HAS_RICH:
        print_section(title)
        try:
            md = Markdown(text)
            _console.print(md)
            print()
            return
        except Exception:
            pass
    # 降级方案
    print_section(title)
    print(f"  {text}")
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
        print_success(f"登录成功（用户: {username}），Cookie 已加密保存")
        count = len(list_sessions())
        if count > 1:
            print_info(f"当前共 {count} 个会话，可用 switch 切换用户")
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
                      f"{_colorize(item['username'], '')}"
                      f"{_get_note_for(item.get('uid', ''))} "
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
                  f"{_colorize(item['username'], '')}"
                  f"{_get_note_for(item.get('uid', '?'))}  "
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


def cmd_problem(args: list[str], _quick_mode: bool = False) -> None:
    """查看题目预览"""
    if not args:
        pid = input(f"{Fore.CYAN}题目ID（如 P1000）：{Style.RESET_ALL}").strip().upper()
        if not pid:
            print_error("题目ID不能为空")
            return
    else:
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

    # 创建代码文件入口（非快速模式时显示）
    if not _quick_mode:
        print()
        c = input(f"  {Fore.CYAN}按 c 创建代码文件并编辑，按回车返回：{Style.RESET_ALL}").strip().lower()
        if c == "c":
            cmd_create([pid])
            return


def cmd_discuss(args: list[str]) -> None:
    """查看讨论帖"""
    if not args:
        did = input(f"{Fore.CYAN}讨论ID（如 962230）：{Style.RESET_ALL}").strip()
        if not did:
            print_error("讨论ID不能为空")
            return
    else:
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
    print(f"  {_colorize(d['author'], d.get('author_color', ''))}"
          f"{_get_note_for(str(d.get('author_uid', '')))}  "
          f"|  {d['time']}  |  {Fore.YELLOW}{d['forum']}{Style.RESET_ALL}  "
          f"|  {d['replyCount']} 条回复")
    print()

    _render_markdown("讨论内容", d.get("content", ""))

    reply_count = d.get("replyCount", 0)
    if reply_count > 0:
        _show_replies(did, reply_count)


def _show_replies(discuss_id: str, total_replies: int) -> None:
    """浏览讨论回复（分页）"""
    page = 1
    per_page = 10
    max_pages = max(1, (total_replies + per_page - 1) // per_page)

    while True:
        print_info(f"正在获取回复（第 {page}/{max_pages} 页）...")
        result = view_discuss_replies(discuss_id, page)

        if result["code"] != 200:
            print_error(f"获取回复失败：{result['msg']}")
            return

        data = result["data"]
        items = data["items"]
        total_count = data.get("totalCount", total_replies)

        if not items:
            if page == 1:
                print_info("暂无回复")
            return

        print_header(f"回复列表（第 {page}/{max_pages} 页 · 共 {total_count} 条）")
        for item in items:
            print(f"\n  {_colorize(item['author'], item.get('color', ''))}"
                  f"{_get_note_for(item.get('author_uid', '?'))}  "
                  f"{Fore.BLUE}{item.get('time', '')}{Style.RESET_ALL}")
            content = item.get("content", "").strip()
            if content:
                for line in content.split("\n"):
                    print(f"      {line}")
            print_divider()

        has_more = page < max_pages and len(items) >= per_page
        if not has_more:
            print_success(f"共 {total_count} 条回复（已全部加载）")
            break
        else:
            print_info(f"第 {page}/{max_pages} 页 · 共 {total_count} 条回复")
            choice = input(
                f"{Fore.CYAN}输入 y 加载下一页，输入数字跳转页数，按回车结束：{Style.RESET_ALL}"
            ).strip().lower()
            if not choice:
                break
            if choice == 'y':
                page += 1
                continue
            try:
                p = int(choice)
                if 1 <= p <= max_pages:
                    page = p
                else:
                    print_error(f"页数超出范围（应为 1-{max_pages}）")
            except ValueError:
                print_error("无效输入，请输入 y、数字或回车")


def cmd_article(args: list[str]) -> None:
    """查看文章"""
    if not args:
        aid = input(f"{Fore.CYAN}文章ID（如 qzywo77y）：{Style.RESET_ALL}").strip()
        if not aid:
            print_error("文章ID不能为空")
            return
    else:
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
    print(f"  {_colorize(d['author'], d.get('author_color', ''))}"
          f"{_get_note_for(str(d.get('author_uid', '')))}  "
          f"|  {d['time']}  |  {Fore.YELLOW}{d['category']}{Style.RESET_ALL}")
    print(f"  赞 {d['upvote']}  |  回复 {d['replyCount']}  |  收藏 {d['favorCount']}")
    print()

    _render_markdown("文章内容", d.get("content", ""))

    reply_count = d.get("replyCount", 0)
    if reply_count > 0:
        _show_article_replies(aid)


def _show_article_replies(article_id: str) -> None:
    """浏览文章回复（游标分页）"""
    after = ""
    total_shown = 0

    while True:
        print_info("正在获取回复..." + (f"（已加载 {total_shown} 条）" if total_shown else ""))
        result = view_article_replies(article_id, after)

        if result["code"] != 200:
            print_error(f"获取回复失败：{result['msg']}")
            return

        data = result["data"]
        items = data["items"]
        next_after = data.get("after", "")

        if not items:
            if total_shown == 0:
                print_info("暂无回复")
            else:
                print_success(f"共加载 {total_shown} 条回复（已全部加载）")
            return

        if total_shown == 0:
            print_header("回复列表")

        for item in items:
            total_shown += 1
            print(f"\n  #{total_shown} {_colorize(item['author'], item.get('color', ''))}"
                  f"{_get_note_for(item.get('author_uid', '?'))}  "
                  f"{Fore.BLUE}{item.get('time', '')}{Style.RESET_ALL}")
            content = item.get("content", "").strip()
            if content:
                for line in content.split("\n"):
                    print(f"      {line}")
            print_divider()

        if not next_after or len(items) < 20:
            print_success(f"共加载 {total_shown} 条回复（已全部加载）")
            break

        print_info(f"已加载 {total_shown} 条回复")
        choice = input(f"{Fore.CYAN}输入 y 加载更多，按回车结束：{Style.RESET_ALL}").strip().lower()
        if choice != 'y':
            break
        after = next_after


def cmd_discusses(args: list[str]) -> None:
    """查看最新讨论（分页浏览并选择查看）"""
    page = 1
    all_items = []
    total_count = None

    while True:
        print_header("最新讨论")
        print_info("正在获取讨论列表...")
        result = view_discuss_list(page)

        if result["code"] == 401:
            print_warning("未登录，请先执行 login")
            return
        elif result["code"] != 200:
            print_error(f"获取失败：{result['msg']}")
            return

        data = result["data"]
        items = data["items"]
        per_page = data.get("perPage", 30)
        total_count = data.get("totalCount", 0)
        max_pages = max(1, (total_count + per_page - 1) // per_page) if total_count else 20

        if not items:
            if page == 1:
                print_warning("暂无讨论")
            else:
                print_info("没有更多讨论了")
            break

        start = len(all_items) + 1
        for i, item in enumerate(items, start):
            prefix = ""
            if item.get("topped"):
                prefix = f"{Fore.MAGENTA}[置顶]{Style.RESET_ALL} "
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                  f"{_colorize(item['username'], item.get('color', ''))}"
                  f"{_get_note_for(item.get('uid', '?'))}  "
                  f"{Fore.BLUE}{item.get('time', '')}{Style.RESET_ALL}"
                  f"  {Fore.CYAN}{item.get('replyCount', 0)} 回复{Style.RESET_ALL}")
            print(f"      {prefix}{Fore.YELLOW}[{item.get('forum', '')}]{Style.RESET_ALL} "
                  f"{item['title']}")
        print()

        all_items.extend(items)
        total = len(all_items)

        has_more = page < max_pages and len(items) > 0
        if not has_more:
            print_success(f"共加载 {total} 条讨论" + (f"（已全部加载）" if page >= max_pages else ""))
            choice = input(f"{Fore.CYAN}输入数字(#1~#{total})查看讨论，按回车结束：{Style.RESET_ALL}").strip()
        else:
            print_info(f"第 {page}/{max_pages} 页 · 共 {total_count} 条讨论")
            choice = input(
                f"{Fore.CYAN}输入 y 加载下一页，输入数字(#1~#{total})查看讨论，按回车结束：{Style.RESET_ALL}"
            ).strip().lower()

        if not choice:
            break

        if has_more and choice == 'y':
            page += 1
            continue

        # 尝试解析为数字序号 → 查看该讨论
        try:
            idx = int(choice)
            if 1 <= idx <= total:
                discuss_id = all_items[idx - 1]["discuss_id"]
                cmd_discuss([str(discuss_id)])
                return
            else:
                print_error(f"序号超出范围（应为 1-{total}）")
        except ValueError:
            print_error("无效输入，请输入 y、数字序号或回车")


def cmd_articles(args: list[str]) -> None:
    """查看最新文章（分页浏览并选择查看）"""
    page = 1
    all_items = []
    total_count = None

    while True:
        print_header("最新文章")
        print_info("正在获取文章列表...")
        result = view_article_list(page)

        if result["code"] == 401:
            print_warning("未登录，请先执行 login")
            return
        elif result["code"] != 200:
            print_error(f"获取失败：{result['msg']}")
            return

        data = result["data"]
        items = data["items"]
        per_page = data.get("perPage", 15)
        total_count = data.get("totalCount", 0)
        max_pages = max(1, (total_count + per_page - 1) // per_page) if total_count else 30

        if not items:
            if page == 1:
                print_warning("暂无文章")
            else:
                print_info("没有更多文章了")
            break

        start = len(all_items) + 1
        for i, item in enumerate(items, start):
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                  f"{_colorize(item['author'], item.get('color', ''))}"
                  f"{_get_note_for(item.get('author_uid', '?'))}  "
                  f"{Fore.BLUE}{item.get('time', '')}{Style.RESET_ALL}"
                  f"  {Fore.CYAN}赞 {item.get('upvote', 0)}  "
                  f"{item.get('replyCount', 0)} 回复{Style.RESET_ALL}")
            print(f"      {Fore.YELLOW}[{item.get('category', '')}]{Style.RESET_ALL} "
                  f"{item['title']}")
        print()

        all_items.extend(items)
        total = len(all_items)

        has_more = page < max_pages and len(items) > 0
        if not has_more:
            print_success(f"共加载 {total} 篇文章" + (f"（已全部加载）" if page >= max_pages else ""))
            choice = input(f"{Fore.CYAN}输入数字(#1~#{total})查看文章，按回车结束：{Style.RESET_ALL}").strip()
        else:
            print_info(f"第 {page}/{max_pages} 页 · 共 {total_count} 篇文章")
            choice = input(
                f"{Fore.CYAN}输入 y 加载下一页，输入数字(#1~#{total})查看文章，按回车结束：{Style.RESET_ALL}"
            ).strip().lower()

        if not choice:
            break

        if has_more and choice == 'y':
            page += 1
            continue

        try:
            idx = int(choice)
            if 1 <= idx <= total:
                article_id = all_items[idx - 1]["lid"]
                cmd_article([str(article_id)])
                return
            else:
                print_error(f"序号超出范围（应为 1-{total}）")
        except ValueError:
            print_error("无效输入，请输入 y、数字序号或回车")


def cmd_punch(args: list[str]) -> None:
    """执行每日打卡"""
    print_header("每日打卡")
    print_info("正在检测打卡状态...")
    status = check_punch_status()
    if status.get("code") == 401:
        print_warning("未登录，请先执行 login")
        return
    if status.get("checked_in"):
        print_success("今日已打卡，无需重复操作")
        _show_fortune()
        return
    print_info("尚未打卡，正在打卡...")
    result = do_punch()
    if result["success"]:
        print_success(result["msg"])
        _show_fortune()
    else:
        print_error(result["msg"])


def _show_fortune() -> None:
    """显示今日运势"""
    print_info("正在获取今日运势...")
    result = get_home()
    if result["code"] == 200:
        data = result["data"]
        fortune = data.get("fortune")
        if fortune:
            print_section("今日运势")
            if "result" in fortune:
                print_field("运势", fortune["result"], indent=4)
            if "do" in fortune:
                for item in fortune["do"]:
                    print_field("宜", f"{item['activity']} —— {item['detail']}", indent=4)
            if "dont" in fortune:
                for item in fortune["dont"]:
                    print_field("忌", f"{item['activity']} —— {item['detail']}", indent=4)


def cmd_problems(args: list[str]) -> None:
    """浏览题目列表"""
    page = 1
    all_items = []
    total_count = None

    while True:
        print_header("题目列表")
        print_info("正在获取...")
        result = view_problem_list(page, "", "")

        if result["code"] == 401:
            print_warning("未登录，请先执行 login")
            return
        elif result["code"] != 200:
            print_error(f"获取失败：{result['msg']}")
            return

        data = result["data"]
        items = data["items"]
        per_page = data.get("perPage", 50)
        total_count = data.get("totalCount", 0)
        max_pages = max(1, (total_count + per_page - 1) // per_page) if total_count else 1

        if not items:
            print_warning("未找到题目")
            return

        start = len(all_items) + 1
        for i, p in enumerate(items, start):
            rate = f"{p['accepted'] / p['submitted'] * 100:.0f}%" if p.get("submitted") else "0%"
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                  f"{Fore.CYAN}{p['pid']}{Style.RESET_ALL}  "
                  f"{Fore.GREEN}{p['name']}{Style.RESET_ALL}")
            print(f"      {Fore.BLUE}{p['difficulty']}{Style.RESET_ALL}  |  "
                  f"提交 {p.get('submitted', 0):,}  |  "
                  f"通过 {p.get('accepted', 0):,}  |  "
                  f"通过率 {rate}")
            if p.get("tags"):
                tags = ", ".join(p["tags"][:5])
                print(f"      {Fore.MAGENTA}标签: {tags}{Style.RESET_ALL}")

        print()

        all_items.extend(items)
        total = len(all_items)

        has_more = page < max_pages and len(items) > 0
        if not has_more:
            print_success(f"共 {total_count} 题，已显示 {total}")
            choice = input(
                f"{Fore.CYAN}输入数字(#1~#{total})查看题目 | e+数字创建代码 | 回车结束：{Style.RESET_ALL}"
            ).strip()
        else:
            print_info(f"第 {page}/{max_pages} 页 · 共 {total_count} 题")
            choice = input(
                f"{Fore.CYAN}y下一页 | 数字查看题目 | e+数字创建代码 | 回车结束：{Style.RESET_ALL}"
            ).strip().lower()

        if not choice:
            break
        if choice == 'y' and has_more:
            page += 1
            continue
        if choice.startswith('e'):
            try:
                idx = int(choice[1:])
                if 1 <= idx <= total:
                    pid = all_items[idx - 1]["pid"]
                    cmd_create([str(pid)])
                    continue
                else:
                    print_error(f"序号超出范围（应为 1-{total}）")
                    continue
            except ValueError:
                print_error("无效输入，e 后应跟数字")
                continue
        try:
            idx = int(choice)
            if 1 <= idx <= total:
                pid = all_items[idx - 1]["pid"]
                cmd_problem([str(pid)])
                return
            else:
                print_error(f"序号超出范围（应为 1-{total}）")
        except ValueError:
            print_error("无效输入")


def cmd_search(args: list[str]) -> None:
    """搜索题目"""
    keyword = args[0] if args else ""
    if not keyword:
        keyword = input(f"{Fore.CYAN}关键词：{Style.RESET_ALL}").strip()
        if not keyword:
            print_error("请输入关键词")
            return
    diff_input = args[1] if len(args) > 1 else ""

    print_header(f"搜索题目：{keyword}")
    if not diff_input:
        print_info("难度格式: 1|2  (1入门 2普及- 3普及/提高- 4普及+/提高 5提高+/省选- 6省选/NOI- 7NOI)")
        diff_input = input(f"{Fore.CYAN}难度（留空=全部）：{Style.RESET_ALL}").strip()

    page = 1
    all_items = []

    while True:
        print_info("正在搜索...")
        result = view_problem_list(page, keyword, diff_input)

        if result["code"] == 401:
            print_warning("未登录，请先执行 login")
            return
        elif result["code"] != 200:
            print_error(f"获取失败：{result['msg']}")
            return

        data = result["data"]
        items = data["items"]
        total_count = data.get("totalCount", 0)
        per_page = data.get("perPage", 50)
        max_pages = max(1, (total_count + per_page - 1) // per_page) if total_count else 1

        if not items:
            print_warning("未找到匹配的题目")
            return

        start = len(all_items) + 1
        for i, p in enumerate(items, start):
            rate = f"{p['accepted'] / p['submitted'] * 100:.0f}%" if p.get("submitted") else "0%"
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                  f"{Fore.CYAN}{p['pid']}{Style.RESET_ALL}  "
                  f"{Fore.GREEN}{p['name']}{Style.RESET_ALL}")
            print(f"      {Fore.BLUE}{p['difficulty']}{Style.RESET_ALL}  |  "
                  f"提交 {p.get('submitted', 0):,}  |  "
                  f"通过 {p.get('accepted', 0):,}  |  "
                  f"通过率 {rate}")

        print()
        all_items.extend(items)
        total = len(all_items)

        if page >= max_pages or len(items) == 0:
            print_success(f"共找到 {total_count} 题，已显示 {total}")
            choice = input(
                f"{Fore.CYAN}输入数字(#1~#{total})查看题目 | e+数字创建代码 | 回车结束：{Style.RESET_ALL}"
            ).strip()
        else:
            print_info(f"第 {page}/{max_pages} 页 · 共 {total_count} 题")
            choice = input(
                f"{Fore.CYAN}y下一页 | 数字查看题目 | e+数字创建代码 | 回车结束：{Style.RESET_ALL}"
            ).strip().lower()

        if not choice:
            break
        if choice == 'y':
            page += 1
            continue
        if choice.startswith('e'):
            try:
                idx = int(choice[1:])
                if 1 <= idx <= total:
                    pid = all_items[idx - 1]["pid"]
                    cmd_create([str(pid)])
                    continue
                else:
                    print_error(f"序号超出范围（应为 1-{total}）")
                    continue
            except ValueError:
                print_error("无效输入，e 后应跟数字")
                continue
        try:
            idx = int(choice)
            if 1 <= idx <= total:
                pid = all_items[idx - 1]["pid"]
                cmd_problem([str(pid)])
                return
            else:
                print_error(f"序号超出范围（应为 1-{total}）")
        except ValueError:
            print_error("无效输入")


def _judgement_reason_color(reason: str, is_punish: bool) -> str:
    """根据原因内容判断显示颜色，覆盖 is_punish 标志"""
    NON_PUNISH_REASONS = {
        "上传站外图片", "上传站外头像", "上传可站外头像",
        "题库志愿者轮换", "题库志愿者轮换，感谢贡献",
        "数学内容审核员轮换", "专区/志愿轮换", "专区/志愿轮换，感谢贡献",
    }
    PUNISH_KEYWORDS = ["棕名", "封禁", "违规", "学术不端"]

    if reason in NON_PUNISH_REASONS:
        return Fore.GREEN
    if any(kw in reason for kw in PUNISH_KEYWORDS):
        return Fore.RED
    return Fore.RED if is_punish else Fore.GREEN


def cmd_judgement(args: list[str]) -> None:
    """查看陶片放逐日志"""
    print_header("陶片放逐")
    print_info("少女祈祷中...")
    result = view_judgement()

    if result["code"] == 401:
        print_warning("未登录，请先执行 login")
        return
    elif result["code"] != 200:
        print_error(f"获取失败：{result['msg']}")
        return

    items = result["data"]["items"]
    if not items:
        print_warning("暂无处罚记录")
        return

    for i, entry in enumerate(items, 1):
        users = entry.get("users", [])
        if users:
            user_strs = []
            for u in users:
                uid_str = str(u.get("uid", "?"))
                name_part = _colorize(u["username"], u.get("color", ""), uid_str)
                note_part = _get_note_for(uid_str)
                user_strs.append(f"{name_part}{note_part}")
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL} "
                  f"{', '.join(user_strs)}  "
                  f"{Fore.BLUE}{entry.get('time', '')}{Style.RESET_ALL}"
                  f"{Fore.CYAN}  [{len(users)} 人]{Style.RESET_ALL}")
        else:
            # 兼容旧格式
            print(f"\n  {Fore.YELLOW}#{i}{Style.RESET_ALL}  "
                  f"{Fore.BLUE}{entry.get('time', '')}{Style.RESET_ALL}")

        for reason in entry.get("reasons", [entry.get("reason", "")]):
            color = _judgement_reason_color(reason, entry.get("is_punish", True))
            print(f"      {color}原因：{reason}{Style.RESET_ALL}")

        added = entry.get("added", 0)
        revoked = entry.get("revoked", 0)
        if added or revoked:
            parts = []
            if revoked:
                parts.append(f"{Fore.YELLOW}撤销 {_desc_perm(revoked)}{Style.RESET_ALL}")
            if added:
                parts.append(f"{Fore.RED}新增 {_desc_perm(added)}{Style.RESET_ALL}")
            print(f"      {' | '.join(parts)}")

    print()
    print_success(f"共 {len(items)} 条记录（已按时间+处罚合并）")


def _desc_perm(perm: int) -> str:
    if perm == 0:
        return "无"
    parts = []
    if perm & 1:
        parts.append("封禁")
    if perm & 131072:
        parts.append("棕名")
    if not parts:
        return f"权限({perm})"
    return "/".join(parts)


def cmd_note(args: list[str]) -> None:
    """管理用户备注"""
    if not args:
        print_error("用法: note <set|del|list> [UID] [备注内容]")
        print_info("  note set <UID> <备注>")
        print_info("  note del <UID>")
        print_info("  note list")
        return

    sub = args[0].lower()
    if sub == "list":
        notes = load_user_notes()
        if not notes:
            print_info("暂无用户备注")
            return
        print_header("用户备注列表")
        for uid, info in notes.items():
            print(f"  {Fore.CYAN}UID:{uid}{Style.RESET_ALL} "
                  f"{Fore.GREEN}{info.get('name', '?')}{Style.RESET_ALL} "
                  f"→ {Fore.MAGENTA}{info.get('note', '')}{Style.RESET_ALL}")
        return

    if sub == "del":
        uid = args[1] if len(args) >= 2 else ""
        if not uid:
            uid = input(f"{Fore.CYAN}要删除备注的 UID：{Style.RESET_ALL}").strip()
        if not uid:
            print_error("UID 不能为空")
            return
        result = delete_user_note(uid)
        if result["success"]:
            print_success(result["msg"])
        else:
            print_error(result["msg"])
        return

    if sub == "set":
        uid = args[1] if len(args) >= 2 else ""
        if not uid:
            uid = input(f"{Fore.CYAN}UID：{Style.RESET_ALL}").strip()
        if not uid:
            print_error("UID 不能为空")
            return
        note_text = " ".join(args[2:]) if len(args) >= 3 else ""
        if not note_text:
            note_text = input(f"{Fore.CYAN}备注内容：{Style.RESET_ALL}").strip()
        if not note_text:
            print_error("备注内容不能为空")
            return
        result = save_user_note(uid, "", note_text)
        if result["success"]:
            print_success(result["msg"])
        else:
            print_error(result["msg"])
        return

    print_error(f"未知子命令: {sub}，可用: set, del, list")


def cmd_verbose(args: list[str]) -> None:
    """切换详细日志"""
    import Server
    Server.VERBOSE = not Server.VERBOSE
    status = "开启" if Server.VERBOSE else "关闭"
    print_success(f"详细日志已{status}")
    if Server.VERBOSE:
        print_info("现在会显示请求 URL 和响应摘要")


# ==============================================
# 代码文件创建功能 (create 命令)
# ==============================================

def _check_nano() -> bool:
    """检查是否有可用的终端编辑器（Git Bash nano | edit.exe | 系统 nano）"""
    if shutil.which("nano"):
        return True
    if sys.platform == "win32" and shutil.which("edit"):
        return True
    return False


def _install_nano() -> bool:
    """自动安装编辑器（优先级：Microsoft.Edit → GNU.Nano 2.8）"""
    # 1) 先试 Microsoft.Edit（Win11 25H2+ 自带，低版本需安装）
    if sys.platform == "win32" and not shutil.which("edit"):
        print_info("正在通过 winget 安装 Microsoft.Edit...")
        ret = os.system("winget install Microsoft.Edit --accept-source-agreements 2>nul")
        if ret == 0 and shutil.which("edit"):
            print_success("Microsoft.Edit 安装成功")
            return True
        print_warning("Microsoft.Edit 安装失败")

    # 2) 兜底安装 GNU.Nano
    if not shutil.which("nano"):
        print_info("正在通过 winget 安装 GNU.Nano 2.8...")
        ret = os.system("winget install GNU.Nano --accept-source-agreements 2>nul")
        if ret == 0:
            print_success("nano 2.8 安装成功")
            return True
        print_warning("GNU.Nano 安装失败")

    return False


def _generate_cpp_template() -> str:
    """生成通用 C++ 代码模板"""
    lines = []
    lines.append("#include <bits/stdc++.h>")
    lines.append("using namespace std;")
    lines.append("")
    lines.append("int main() {")
    lines.append("    ios::sync_with_stdio(false);")
    lines.append("    cin.tie(nullptr);")
    lines.append("")
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def _open_in_nano(filepath: str) -> None:
    """在新窗口中打开编辑器（优先级：Git nano → edit.exe → 系统 nano → 记事本）"""
    abs_path = os.path.abspath(filepath)
    filename = os.path.basename(abs_path)

    git_nano = r"C:\Program Files\Git\usr\bin\nano.exe"
    bash_path = r"C:\Program Files\Git\bin\bash.exe"
    has_git_nano = os.path.exists(git_nano) and os.path.exists(bash_path)

    if sys.platform != "win32":
        # Linux/Mac → 当前终端运行 nano
        print_info("正在当前终端中打开 nano...")
        os.system(f'nano "{abs_path}"')
        return

    # --- Windows 以下 ---

    # 优先级 1: Git Bash nano 8.7（已有，无需安装）
    if has_git_nano:
        safe_path = abs_path.replace("\\", "/")
        title = f"nano - {filename}"
        inner = f'nano "{safe_path}"; echo; read -p "按回车关闭此窗口..."'
        os.system(f'start "{title}" "{bash_path}" --login -c \'{inner}\'')
        print_success("nano 8.7 已在新的窗口中启动")
        return

    # 优先级 2: edit.exe（已存在或刚通过 Microsoft.Edit 安装）
    if shutil.which("edit"):
        title = f"edit - {filename}"
        os.system(f'start "{title}" edit "{abs_path}"')
        print_success("edit.exe 已在新的窗口中启动")
        return

    # 优先级 3: 系统 nano（可能刚通过 GNU.Nano 安装）
    if shutil.which("nano"):
        title = f"nano - {filename}"
        os.system(f'start "{title}" nano "{abs_path}"')
        print_success("nano 已在新的窗口中启动")
        return

    # 兜底：系统记事本
    title = f"notepad - {filename}"
    os.system(f'start "{title}" notepad "{abs_path}"')
    print_success("记事本已打开")


def cmd_create(args: list[str]) -> None:
    """创建 C++ 代码文件并用 nano 编辑"""
    print_header("创建 C++ 代码文件")

    # 1. 确定文件名
    filename = ""
    if args:
        first = args[0]
        # 检测是否是 PID（如 P1000）
        if re.match(r'^[A-Za-z]\d+$', first):
            filename = first.upper() + ".cpp"
        else:
            filename = first

    if not filename:
        filename = input("  文件名（留空默认 template.cpp）：").strip()

    if not filename:
        filename = "template.cpp"
    elif not filename.endswith(".cpp"):
        filename += ".cpp"

    # 2. 可选：关联题目（在源窗口显示题目，nano 只使用通用模板）
    choice = input("  是否关联题目？(y/n, 默认n)：").strip().lower()
    if choice == "y":
        pid = input("  题目 ID（如 P1000）：").strip().upper()
        if re.match(r'^[A-Z]\d+$', pid):
            print_info(f"正在显示题目 {pid}...")
            # 在源窗口调用 cmd_problem 完整显示题目（快速模式，不自带创建提示）
            cmd_problem([pid], _quick_mode=True)
            # 用 PID 作为文件名
            filename = f"{pid}.cpp"
            print_success(f"已关联题目 {pid}")
        else:
            print_warning("无效的题目 ID，跳过关联")

    # 3. 创建文件
    filepath = os.path.join(os.getcwd(), filename)
    if os.path.exists(filepath):
        overwrite = input(
            f"  文件 {filename} 已存在，是否覆盖？(y/n, 默认n)："
        ).strip().lower()
        if overwrite != "y":
            print_info("操作已取消")
            return

    template = _generate_cpp_template()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(template)
        print_success(f"文件 {filename} 已创建")
    except Exception as e:
        print_error(f"创建文件失败：{e}")
        return

    # 4. 检查编辑器并打开（自动降级：Git nano → edit.exe → 系统 nano → 记事本）
    if not _check_nano():
        print_warning("未检测到终端编辑器")
        install = input("  是否自动安装编辑器？(y/n, 默认y)：").strip().lower()
        if install != "n":
            _install_nano()
        else:
            print_info("跳过安装")
    # 无论安装是否成功，都尝试打开（最差也有记事本兜底）
    _open_in_nano(filepath)


def cmd_color(args: list[str]) -> None:
    """管理用户自定义颜色"""
    if not args:
        print_error("用法: color <set|del|list> [UID] [颜色名]")
        print_info("  可用颜色: Red Purple Orange Blue Green Cyan Gold Brown Gray")
        return

    sub = args[0].lower()
    if sub == "list":
        colors = load_user_colors()
        if not colors:
            print_info("暂无自定义颜色")
            return
        print_header("自定义颜色列表")
        for uid, c in colors.items():
            print(f"  {Fore.CYAN}UID:{uid}{Style.RESET_ALL} → {_LUOGU_COLOR_MAP.get(c, c)}{c}{Style.RESET_ALL}")
        return

    if sub == "del":
        uid = args[1] if len(args) >= 2 else ""
        if not uid:
            uid = input(f"{Fore.CYAN}UID：{Style.RESET_ALL}").strip()
        if not uid:
            print_error("UID 不能为空")
            return
        result = delete_user_color(uid)
        if result["success"]:
            print_success(result["msg"])
        else:
            print_error(result["msg"])
        return

    if sub == "set":
        uid = args[1] if len(args) >= 2 else ""
        if not uid:
            uid = input(f"{Fore.CYAN}UID：{Style.RESET_ALL}").strip()
        if not uid:
            print_error("UID 不能为空")
            return
        color = args[2] if len(args) >= 3 else ""
        if not color:
            color = input(f"{Fore.CYAN}颜色名（Red Purple Orange Blue Green Cyan Gold Brown Gray）：{Style.RESET_ALL}").strip()
        valid = {"Red", "Purple", "Orange", "Blue", "Green", "Cyan", "Gold", "Brown", "Gray"}
        if color not in valid:
            print_error(f"无效颜色: {color}，可用: {' '.join(sorted(valid))}")
            return
        result = save_user_color(uid, color)
        if result["success"]:
            print_success(result["msg"])
        else:
            print_error(result["msg"])
        return

    print_error(f"未知子命令: {sub}，可用: set, del, list")


def cmd_logout(args: list[str]) -> None:
    """退出登录（可指定用户名）"""
    print_header("退出登录")
    if args:
        # 退出指定用户
        target = args[0]
        users = list_sessions()
        if target not in users:
            print_error(f"未找到用户 {target} 的会话")
            print_info(f"当前已登录用户: {', '.join(users) if users else '无'}")
            return
        confirm = input(f"确定要清除用户 {Fore.CYAN}{target}{Style.RESET_ALL} 的登录状态吗？(y/n)：").strip().lower()
        if confirm == "y":
            result = clear_cookie(target)
            if result["status"]:
                print_success(result["msg"])
            else:
                print_error(result["msg"])
        else:
            print_info("已取消")
        return

    # 退出当前用户
    current = get_current_user()
    if not current:
        print_info("当前未登录")
        sessions = list_sessions()
        if sessions:
            print_info(f"已保存的会话: {', '.join(sessions)}")
            print_info("使用 logout <用户名> 清除指定会话")
        return
    confirm = input(f"确定要清除当前用户 {Fore.CYAN}{current}{Style.RESET_ALL} 的登录状态吗？(y/n)：").strip().lower()
    if confirm == "y":
        result = clear_cookie()
        if result["status"]:
            print_success(result["msg"])
        else:
            print_error(result["msg"])
    else:
        print_info("已取消")


def cmd_sessions(args: list[str]) -> None:
    """列出所有已保存的会话"""
    users = get_session_users()
    if not users:
        print_info("没有已保存的会话")
        return
    print_header("已保存的会话")
    for u in users:
        tag = f" {Fore.GREEN}← 当前{Style.RESET_ALL}" if u.get("current") else ""
        print(f"  {Fore.CYAN}{u['username']}{Style.RESET_ALL}{tag}")
    print()
    print_success(f"共 {len(users)} 个会话")


def cmd_switch(args: list[str]) -> None:
    """切换当前用户"""
    sessions = list_sessions()
    if not sessions:
        print_warning("没有已保存的会话，请先 login")
        return
    current = get_current_user()
    print_header("切换用户")
    for i, user in enumerate(sessions, 1):
        tag = f" {Fore.GREEN}← 当前{Style.RESET_ALL}" if user == current else ""
        print(f"  {Fore.YELLOW}#{i}{Style.RESET_ALL} {Fore.CYAN}{user}{Style.RESET_ALL}{tag}")
    print()

    if args and args[0] in sessions:
        target = args[0]
    else:
        inp = input(f"{Fore.CYAN}输入序号或用户名切换，回车取消：{Style.RESET_ALL}").strip()
        if not inp:
            print_info("已取消")
            return
        sessions_list = list(sessions)
        try:
            idx = int(inp)
            if 1 <= idx <= len(sessions_list):
                target = sessions_list[idx - 1]
            else:
                print_error(f"序号超出范围（应为 1-{len(sessions_list)}）")
                return
        except ValueError:
            if inp in sessions:
                target = inp
            else:
                print_error(f"未知用户: {inp}")
                return

    result = switch_session(target)
    if result["success"]:
        print_success(result["msg"])
    else:
        print_error(result["msg"])


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
# 免责声明
# ==============================================

DISCLAIMER_FILE = "disclaimer_accepted"
DISCLAIMER_PATH = "DISCLAIMER.md"


def _show_disclaimer() -> bool:
    """
    显示免责声明与隐私声明（首次使用 / 版本更新时）。
    返回 True 表示用户同意，False 表示拒绝。
    """
    try:
        with open(DISCLAIMER_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return True

    current_version = VERSION.replace("v", "")

    if os.path.exists(DISCLAIMER_FILE):
        try:
            with open(DISCLAIMER_FILE, "r", encoding="utf-8") as f:
                accepted_version = f.read().strip()
            if accepted_version == current_version:
                return True
        except Exception:
            pass

    # 直接渲染全量内容，不走分页逻辑（避免双 input 冲突）
    cleaned = _simplify_latex(content)
    _render_chunk("免责声明与隐私声明", cleaned)

    print(f"{Fore.YELLOW}{'─'*50}{Style.RESET_ALL}")
    while True:
        choice = input(
            f"{Fore.CYAN}请输入 y（同意并继续）/ n（拒绝并退出）：{Style.RESET_ALL}"
        ).strip().lower()
        if choice == "y":
            try:
                with open(DISCLAIMER_FILE, "w", encoding="utf-8") as f:
                    f.write(current_version)
            except Exception:
                pass
            return True
        elif choice == "n":
            print_error("您已拒绝免责声明，程序退出。")
            print_info("如改变主意，请删除 disclaimer_accepted 文件后重新运行。")
            return False
        else:
            print_warning("请输入 y 或 n")


def cmd_disclaimer(args: list[str]) -> None:
    """查看免责声明与隐私声明"""
    print_header("免责声明与隐私声明")
    try:
        with open(DISCLAIMER_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        _render_markdown("免责声明与隐私声明", content)
    except FileNotFoundError:
        print_warning("免责声明文件不存在")


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
    "discusses": ("查看最新讨论（可翻页选择）", cmd_discusses),
    "article":  ("查看文章 <ID>", cmd_article),
    "articles": ("查看最新文章（可翻页选择）", cmd_articles),
    "logout":   ("退出登录(清除Cookie)", cmd_logout),
    "punch":    ("每日打卡", cmd_punch),
    "problems": ("题目列表", cmd_problems),
    "search":   ("搜索题目", cmd_search),
    "judgement":("陶片放逐（处罚日志）", cmd_judgement),
    "note":     ("管理用户备注", cmd_note),
    "color":    ("管理用户自定义颜色", cmd_color),
    "create":   ("创建C++代码文件并用nano编辑", cmd_create),
    "verbose":  ("切换详细日志", cmd_verbose),
    "sessions": ("列出所有已保存的会话", cmd_sessions),
    "switch":   ("切换当前用户", cmd_switch),
    "disclaimer": ("查看免责声明与隐私声明", cmd_disclaimer),
    "help":     ("显示帮助信息", cmd_help),
    "exit":     ("退出程序", cmd_exit),
    "quit":     ("退出程序", cmd_exit),
}

ALIASES = {
    "cls": "help",
    "new": "create",
    "ed": "create",
    "clear": "help",
    "？": "help",
    "h": "help",
    "q": "exit",
    "quit": "exit",
    "user": "profile",
    "p": "problem",
    "d": "discuss",
    "dis": "discuss",
    "ds": "discusses",
    "a": "article",
    "art": "article",
    "as": "articles",
    "pk": "punch",
    "ps": "problems",
    "sh": "search",
    "jd": "judgement",
    "nt": "note",
    "cl": "color",
    "vb": "verbose",
    "ss": "sessions",
    "sw": "switch",
    "users": "sessions",
    "account": "switch",
}


def main():
    # ---- 首次使用：显示免责声明 ----
    if not _show_disclaimer():
        sys.exit(0)

    print(f"\n{Style.BRIGHT}{Fore.CYAN}╔{'═'*40}╗")
    print(f"║{' ' * 12}洛谷命令行工具{' ' * 13}║")
    print(f"║{' ' * 15}{VERSION}{' ' * 16}║")
    print(f"╚{'═'*40}╝{Style.RESET_ALL}")

    current_user = get_current_user()
    if current_user:
        sessions = list_sessions()
        if len(sessions) > 1:
            print_info(f"当前用户: {current_user}  （共 {len(sessions)} 个会话，switch 切换）")
        else:
            print_info(f"当前用户: {current_user}")
    if is_logged_in():
        # 检查打卡状态
        try:
            status = check_punch_status()
            if status.get("code") == 200 and not status.get("checked_in"):
                choice = input(
                    f"{Fore.YELLOW}今天还没打卡，要打卡吗？(y/n)：{Style.RESET_ALL}"
                ).strip().lower()
                if choice == 'y':
                    result = do_punch()
                    if result["success"]:
                        print_success(result["msg"])
                    else:
                        print_error(result["msg"])
        except Exception:
            pass
        print()
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
