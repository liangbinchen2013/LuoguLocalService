# -*- coding: utf-8 -*-
"""
洛谷本地服务 - 后端引擎
========================
提供登录、页面访问、用户资料解析、主页解析等功能。

核心函数均返回 dict，CLI 入口 main() 负责 JSON 序列化。
可直接导入使用：from Server import login, view_page, get_profile, get_home
"""

import warnings
warnings.filterwarnings("ignore")
import base64
import requests
import argparse
import time
import re
import os
import random
import json
import sys
import getpass


# ==============================================
# 【模块1：全局配置】
# ==============================================
class Config:
    # 洛谷接口
    LOGIN_PAGE = "https://www.luogu.com.cn/auth/login"
    CAPTCHA_API = "https://www.luogu.com.cn/lg4/captcha"
    LOGIN_API = "https://www.luogu.com.cn/do-auth/password"
    C3VK_REFRESH_URL = "https://www.luogu.com.cn/images/index/step1.png"
    # OCR配置
    OCR_API = "https://ocr.lbcoj.top/"
    CAPTCHA_PATH = "ocr.jpg"
    # Cookie持久化
    COOKIE_SAVE_PATH = "luogu_cookies.json"
    # 默认访问地址
    DEFAULT_VIEW_URL = "https://www.luogu.com.cn/user/1432496"
    # 验证码最大重试次数
    MAX_CAPTCHA_RETRY = 3
    # 密码环境变量名称（用于 CLI 模式安全输入）
    PASSWORD_ENV_VAR = "LUOGU_PASSWORD"


# ==============================================
# 【模块2：请求头】
# ==============================================
class Headers:
    BASE = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": Config.LOGIN_PAGE,
    }


# ==============================================
# 【模块3：刷新C3VK Cookie】
# ==============================================
def refresh_c3vk(session: requests.Session) -> bool:
    """刷新 C3VK Cookie，用于绕过洛谷反爬机制"""
    try:
        session.get(Config.C3VK_REFRESH_URL, headers=Headers.BASE,
                    allow_redirects=True, timeout=5)
        return True
    except Exception:
        return False


# ==============================================
# 【模块4：Cookie 保存/加载】
# ==============================================
def save_cookie(session: requests.Session) -> dict:
    """将会话 Cookie 持久化到本地文件"""
    try:
        cookies = session.cookies.get_dict()
        with open(Config.COOKIE_SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False)
        return {"status": True, "data": cookies}
    except Exception as e:
        return {"status": False, "msg": str(e)}


def load_cookie() -> requests.Session | None:
    """从本地文件加载 Cookie，返回 Session 或 None"""
    if not os.path.exists(Config.COOKIE_SAVE_PATH):
        return None
    try:
        session = requests.Session()
        with open(Config.COOKIE_SAVE_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for k, v in cookies.items():
            session.cookies.set(k, v)
        refresh_c3vk(session)
        return session
    except Exception:
        return None


def clear_cookie() -> dict:
    """清除本地保存的 Cookie 文件"""
    try:
        if os.path.exists(Config.COOKIE_SAVE_PATH):
            os.remove(Config.COOKIE_SAVE_PATH)
        return {"status": True, "msg": "Cookie 已清除"}
    except Exception as e:
        return {"status": False, "msg": f"清除失败：{str(e)}"}


def is_logged_in() -> bool:
    """检查是否已登录（本地是否有 Cookie 文件）"""
    return load_cookie() is not None


# ==============================================
# 【模块5：验证码下载+OCR识别】
# ==============================================
def get_captcha(session: requests.Session) -> dict:
    """下载验证码图片并通过 OCR API 识别，返回识别结果"""
    try:
        if os.path.exists(Config.CAPTCHA_PATH):
            os.remove(Config.CAPTCHA_PATH)

        time.sleep(random.uniform(1, 1.5))
        timestamp = f"{time.time() * 1000}.{random.randint(100, 999)}"
        resp = session.get(f"{Config.CAPTCHA_API}?_t={timestamp}",
                           headers=Headers.BASE, timeout=10)
        resp.raise_for_status()

        with open(Config.CAPTCHA_PATH, "wb") as f:
            f.write(resp.content)

        with open(Config.CAPTCHA_PATH, "rb") as f:
            img_base64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

        ocr_res = requests.post(Config.OCR_API,
                                json={"image": img_base64}, timeout=10).json()

        captcha = str(ocr_res.get("data", "")).strip().upper()
        if len(captcha) == 4:
            return {"status": True, "code": captcha}
        return {"status": False, "msg": "验证码格式错误"}
    except Exception as e:
        return {"status": False, "msg": str(e)}
    finally:
        if os.path.exists(Config.CAPTCHA_PATH):
            os.remove(Config.CAPTCHA_PATH)


# ==============================================
# 【模块6：登录功能】
# ==============================================
def login(user: str, pwd: str) -> dict:
    """
    洛谷登录（核心函数）

    参数：
        user: 用户名或邮箱
        pwd:  密码

    返回：
        {"code": 200, "msg": "登录成功", "cookies": {...}}  或
        {"code": 400/500, "msg": "错误描述"}
    """
    session = requests.Session()
    try:
        resp = session.get(Config.LOGIN_PAGE, headers=Headers.BASE, timeout=10)
        csrf_match = re.search(r'<meta name="csrf-token" content="(.*?)">', resp.text)
        if not csrf_match:
            return {"code": 500, "msg": "无法获取 CSRF Token"}
        csrf = csrf_match.group(1)

        refresh_c3vk(session)

        # 获取验证码（最多重试 MAX_CAPTCHA_RETRY 次）
        captcha = ""
        for _ in range(Config.MAX_CAPTCHA_RETRY):
            cap_res = get_captcha(session)
            if cap_res["status"]:
                captcha = cap_res["code"]
                break

        if not captcha:
            return {"code": 500, "msg": "验证码获取失败"}

        login_headers = {
            **Headers.BASE,
            "Content-Type": "application/json",
            "Origin": "https://www.luogu.com.cn",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf,
        }

        login_data = {"username": user, "password": pwd, "captcha": captcha}
        for _ in range(Config.MAX_CAPTCHA_RETRY):
            resp = session.post(Config.LOGIN_API, json=login_data,
                                headers=login_headers, allow_redirects=False, timeout=10)
            if resp.status_code == 200:
                break
            # 验证码错误 → 重新获取
            cap_res = get_captcha(session)
            if cap_res["status"]:
                login_data["captcha"] = cap_res["code"]

        if resp.status_code != 200:
            return {"code": 400, "msg": "登录失败（账号/密码/验证码错误）"}

        save_cookie(session)
        # 返回前清除密码
        pwd = ""
        return {
            "code": 200,
            "msg": "登录成功",
            "cookies": session.cookies.get_dict(),
        }

    except Exception as e:
        return {"code": 500, "msg": f"服务器错误：{str(e)}"}
    finally:
        # 确保敏感信息被清除
        pwd = ""


# 保留旧函数名作为别名（兼容性，但标注为 deprecated）
def luogu_login(user: str, pwd: str) -> dict:
    """已弃用，请使用 login()"""
    return login(user, pwd)


# ==============================================
# 【模块7：页面访问】
# ==============================================
def view_page(url: str = None) -> dict:
    """
    访问洛谷页面（需要已登录）

    参数：
        url: 目标 URL，留空使用默认地址

    返回：
        {"code": 200, "msg": "访问成功", "url": "...", "html": "..."}  或
        {"code": 401, "msg": "未登录"} / {"code": 500, "msg": "错误"}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    target = url or Config.DEFAULT_VIEW_URL
    try:
        resp = session.get(target, headers=Headers.BASE, timeout=10)
        resp.raise_for_status()
        return {
            "code": 200,
            "msg": "访问成功",
            "url": target,
            "html": resp.text,
        }
    except Exception as e:
        return {"code": 500, "msg": f"访问失败：{str(e)}"}


# ==============================================
# 【模块8：HTML 解析工具】
# ==============================================

def _strip_html(html_content: str) -> str:
    """去除 HTML 标签，提取纯文本"""
    return re.sub(r'<[^>]+>', '', html_content).strip()


def _extract_href(html_content: str) -> str | None:
    """从 HTML 中提取 href 链接"""
    m = re.search(r'href="(.*?)"', html_content)
    return m.group(1) if m else None


def _extract_info_rows(html: str) -> list[tuple[str, dict]]:
    """
    提取页面中所有 l-flex-info-row 信息行

    返回：[(标签, {text, href}), ...]
    """
    pattern = re.compile(
        r'<div class="l-flex-info-row"><span>(.*?)</span><div class="right">(.*?)</div></div>',
        re.DOTALL,
    )
    rows = []
    for label, value_html in pattern.findall(html):
        text = _strip_html(value_html)
        href = _extract_href(value_html)
        rows.append((label.strip(), {"text": text, "href": href}))
    return rows


def _extract_stat_pairs(html: str) -> dict[str, str]:
    """
    提取页面中 stat-text 统计对（关注/粉丝/提交/通过/排名/等级分）

    返回：{"关注": "8", "粉丝": "12", ...}
    """
    pattern = re.compile(
        r'<span[^>]*class="stat-text name"[^>]*>(.*?)</span>'
        r'\s*<span[^>]*class="stat-text value"[^>]*>(.*?)</span>'
    )
    result = {}
    for name, value in pattern.findall(html):
        result[name.strip()] = value.strip()
    return result


def parse_user_profile(html: str) -> dict:
    """
    解析用户资料页 HTML，提取结构化数据

    返回：
        {
            "stats": {"关注": "8", "粉丝": "12", ...},
            "basic_info": {"用户编号": "...", "用户类型": "...", "注册时间": "..."},
            "guzhi": {"基础信用": "100", "练习情况": "62", ...},
            "contest_rating": {"等级分": "1007", "评定比赛": "...", ...},
        }
    """
    result = {}

    # 1) 头部统计数据（关注/粉丝/提交/通过/排名/等级分）
    result["stats"] = _extract_stat_pairs(html)

    # 2) 信息行解析（按卡片顺序分类）
    rows = _extract_info_rows(html)

    basic_info = {}
    guzhi = {}
    contest_rating = {}
    current_section = "basic_info"  # basic_info → guzhi → contest_rating

    # 已知的 guzhi 字段（用于检测 section 切换）
    GUZHI_FIELDS = {"基础信用", "练习情况", "社区贡献", "比赛情况", "获得成就", "总咕值"}

    for label, info in rows:
        if label in GUZHI_FIELDS:
            current_section = "guzhi"
            guzhi[label] = info
        elif label == "达成时间":
            # "达成时间" 同时出现在 咕值 和 比赛等级分 中
            if current_section == "guzhi":
                guzhi[label] = info
                current_section = "contest_rating"
            else:
                contest_rating[label] = info
        elif label in ("用户编号", "用户类型", "注册时间"):
            basic_info[label] = info
        elif label == "等级分":
            contest_rating[label] = info
        elif label == "评定比赛":
            contest_rating[label] = info
        else:
            # 未知字段，归入当前 section
            if current_section == "basic_info":
                basic_info[label] = info
            elif current_section == "guzhi":
                guzhi[label] = info
            else:
                contest_rating[label] = info

    if basic_info:
        result["basic_info"] = basic_info
    if guzhi:
        result["guzhi"] = guzhi
    if contest_rating:
        result["contest_rating"] = contest_rating

    return result


def parse_home_page(html: str) -> dict:
    """
    解析登录后主页 HTML，提取运势、打卡、动态等信息

    返回：
        {
            "username": "...",
            "fortune": {"result": "小吉", "do": [...], "dont": [...], ...},
            "checkin_days": 85,
            "feed": [{"user": "...", "content": "...", "time": "..."}, ...]
        }
    """
    result = {}

    # 1) 用户名
    user_match = re.search(
        r'<a class="lg-fg-red lg-bold"[^>]*href="/user/\d+"[^>]*target="_blank">(.*?)</a>\s*的运势',
        html,
    )
    if user_match:
        result["username"] = user_match.group(1).strip()

    # 2) 运势结果
    fortune_match = re.search(
        r'<span class="lg-punch-result lg-fg-red">§\s*(.*?)\s*§</span>', html
    )
    if fortune_match:
        result.setdefault("fortune", {})["result"] = fortune_match.group(1).strip()

    # 3) 宜/忌
    do_items = re.findall(
        r'宜：</span>(.*?)<br>\s*<span class="lg-small">(.*?)</span>', html
    )
    dont_items = re.findall(
        r'忌：</span>(.*?)<br>\s*<span class="lg-small">(.*?)</span>', html
    )
    fortune = {}
    if do_items:
        fortune["do"] = [
            {"activity": d.strip(), "detail": det.strip()}
            for d, det in do_items
        ]
    if dont_items:
        fortune["dont"] = [
            {"activity": d.strip(), "detail": det.strip()}
            for d, det in dont_items
        ]
    if fortune:
        result["fortune"] = {**result.get("fortune", {}), **fortune}

    # 4) 打卡天数
    checkin_match = re.search(
        r'你已经在洛谷连续打卡了 <strong>(\d+)</strong> 天', html
    )
    if checkin_match:
        result["checkin_days"] = int(checkin_match.group(1))

    # 5) 动态（Feed）
    feed_items = re.findall(
        r'<li class="am-comment am-comment-primary feed-li">.*?'
        r'<a[^>]*class="lg-fg-orange lg-bold"[^>]*href="/user/(\d+)"[^>]*>'
        r'(.*?)</a>.*?'
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?'
        r'<span class="feed-comment"><p>(.*?)</p></span>',
        html,
        re.DOTALL,
    )
    feed = []
    for uid, uname, time_str, content in feed_items:
        feed.append({
            "uid": uid.strip(),
            "username": uname.strip(),
            "time": time_str.strip(),
            "content": _strip_html(content),
        })
    if feed:
        result["feed"] = feed

    return result


# ==============================================
# 【模块9：高级功能（Cookie + 抓取 + 解析）】
# ==============================================

def get_profile(url: str = None) -> dict:
    """
    获取并解析用户资料（需要已登录）

    参数：
        url: 用户主页 URL，留空使用默认

    返回：
        {"code": 200, "data": {...}}  或
        {"code": 401, "msg": "未登录"} / {"code": 500, "msg": "错误"}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    target = url or Config.DEFAULT_VIEW_URL
    try:
        resp = session.get(target, headers=Headers.BASE, timeout=10)
        resp.raise_for_status()
        profile = parse_user_profile(resp.text)
        return {
            "code": 200,
            "msg": "获取成功",
            "url": target,
            "data": profile,
        }
    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


def get_home() -> dict:
    """
    获取并解析洛谷首页（需要已登录）

    返回：
        {"code": 200, "data": {...}}  或
        {"code": 401, "msg": "未登录"} / {"code": 500, "msg": "错误"}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        resp = session.get("https://www.luogu.com.cn/", headers=Headers.BASE, timeout=10)
        resp.raise_for_status()
        home_data = parse_home_page(resp.text)
        return {
            "code": 200,
            "msg": "获取成功",
            "data": home_data,
        }
    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


# ==============================================
# 【模块10：CLI 命令行入口】
# ==============================================

def _resolve_password(args) -> str:
    """
    安全解析密码，优先级：
    1. --password-stdin（从 stdin 读取）
    2. LUOGU_PASSWORD 环境变量
    3. 交互式 getpass 输入
    4. --pwd（向后兼容，不推荐）
    """
    if args.password_stdin:
        return sys.stdin.readline().strip()

    env_pwd = os.environ.get(Config.PASSWORD_ENV_VAR)
    if env_pwd:
        return env_pwd

    if args.pwd:
        warnings.warn(
            "[安全警告] 通过 --pwd 参数传入密码会在进程列表中可见，"
            "建议使用 --password-stdin 或 LUOGU_PASSWORD 环境变量",
            UserWarning,
        )
        return args.pwd

    return getpass.getpass("密码（输入隐藏）：").strip()


def main():
    """CLI 入口：解析命令行参数，调用核心函数，输出 JSON"""
    parser = argparse.ArgumentParser(description="洛谷本地服务 - 后端引擎")
    parser.error = lambda msg: (
        print(json.dumps({"code": 50001, "msg": msg}, ensure_ascii=False)),
        exit(),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # login 子命令
    login_p = subparsers.add_parser("login", help="登录洛谷")
    login_p.add_argument("--user", required=True, help="用户名或邮箱")
    login_p.add_argument(
        "--pwd",
        help="[不推荐] 密码（命令行可见）。省略时将按优先级使用："
             "--password-stdin > LUOGU_PASSWORD 环境变量 > 交互式输入",
    )
    login_p.add_argument(
        "--password-stdin",
        action="store_true",
        help="从标准输入读取密码（用于脚本管道，更安全）",
    )

    # view 子命令
    view_p = subparsers.add_parser("view", help="访问洛谷页面")
    view_p.add_argument("--url", help="自定义访问地址（留空使用默认）")

    # profile 子命令
    profile_p = subparsers.add_parser("profile", help="查看用户资料")
    profile_p.add_argument("--url", help="用户主页地址（留空使用默认）")

    # home 子命令
    subparsers.add_parser("home", help="查看主页运势/动态")

    # logout 子命令
    subparsers.add_parser("logout", help="清除本地 Cookie（注销）")

    args = parser.parse_args()

    # ---- 命令分发 ----
    if args.command == "login":
        password = _resolve_password(args)
        result = login(args.user, password)
        # 清除本地变量中的密码
        password = ""
        print(json.dumps(result, ensure_ascii=False))

    elif args.command == "view":
        result = view_page(args.url)
        print(json.dumps(result, ensure_ascii=False))

    elif args.command == "profile":
        result = get_profile(args.url)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "home":
        result = get_home()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "logout":
        result = clear_cookie()
        print(json.dumps(result, ensure_ascii=False))

    else:
        print(json.dumps({"code": 50001}, ensure_ascii=False))


if __name__ == "__main__":
    main()
