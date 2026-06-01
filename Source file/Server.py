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
from datetime import datetime


# 版本号
VERSION = "v1.0.0"


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
    # 犇犇API
    FEED_WATCHING_URL = "https://www.luogu.com.cn/feed/watching"
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
# 【模块7：HTML 解析工具 + JSON 数据提取】
# ==============================================

def _strip_html(html_content: str) -> str:
    """去除 HTML 标签，提取纯文本"""
    return re.sub(r'<[^>]+>', '', html_content).strip()


def _extract_lentille_json(html: str) -> dict | None:
    """
    从页面HTML中提取 lentille-context JSON 数据
    （洛谷使用 Vue SPA，数据通过此 script 标签嵌入）
    """
    m = re.search(
        r'<script id="lentille-context"[^>]*type="application/json">(.*?)</script>',
        html, re.DOTALL,
    )
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def parse_user_profile(html: str) -> dict:
    """
    从 lentille-context JSON 解析用户资料结构化数据

    返回：
        {
            "stats": {"关注": "8", "粉丝": "12", "提交": "707", ...},
            "basic_info": {"用户编号": {"text": "1432496"}, "用户类型": {"text": "..."}, ...},
            "guzhi": {"基础信用": {"text": "100"}, ...},
            "contest_rating": {"等级分": {"text": "1007"}, "评定比赛": {"text": "..."}, ...},
        }
    """
    ctx = _extract_lentille_json(html)
    if not ctx:
        return {}

    result = {}
    d = ctx.get("data", {})
    user = d.get("user", {})

    # ── 1) 统计数据 ──
    stats = {}
    stats["关注"] = str(user.get("followingCount", 0))
    stats["粉丝"] = str(user.get("followerCount", 0))
    stats["提交"] = str(user.get("submittedProblemCount", 0))
    stats["通过"] = str(user.get("passedProblemCount", 0))

    ranking = user.get("ranking", 0)
    if ranking >= 1000:
        stats["排名"] = f"{ranking / 1000:.2f}k"
    else:
        stats["排名"] = str(ranking)

    # 等级分取最新 elo
    elo_list = d.get("elo", [])
    if elo_list:
        latest_elo = elo_list[0]
        stats["等级分"] = str(latest_elo.get("rating", 0))
    result["stats"] = stats

    # ── 2) 基本信息 ──
    basic = {}
    basic["用户编号"] = {"text": str(user.get("uid", ""))}
    basic["用户类型"] = {
        "text": "管理员" if user.get("isAdmin")
                else "封禁用户" if user.get("isBanned")
                else "普通用户",
    }
    reg_ts = user.get("registerTime", 0)
    if reg_ts:
        dt = datetime.fromtimestamp(reg_ts)
        basic["注册时间"] = {"text": dt.strftime("%Y-%m-%d")}
    result["basic_info"] = basic

    # ── 3) 咕值 ──
    gu = d.get("gu", {})
    scores = gu.get("scores", {})
    if scores:
        guzhi = {}
        label_map = {
            "basic": "基础信用", "practice": "练习情况",
            "social": "社区贡献", "contest": "比赛情况",
            "prize": "获得成就", "rating": "总咕值",
        }
        for key, label in label_map.items():
            val = scores.get(key)
            if val is not None:
                guzhi[label] = {"text": str(val)}
        gu_ts = gu.get("time", 0)
        if gu_ts:
            dt = datetime.fromtimestamp(gu_ts)
            guzhi["达成时间"] = {"text": dt.strftime("%Y-%m-%d")}
        result["guzhi"] = guzhi

    # ── 4) 比赛等级分 ──
    if elo_list:
        latest = elo_list[0]
        cr = {}
        cr["等级分"] = {"text": str(latest.get("rating", 0))}
        contest = latest.get("contest", {})
        if contest.get("name"):
            cr["评定比赛"] = {"text": contest["name"]}
        if contest.get("id"):
            cr["评定比赛"]["href"] = f"/contest/{contest['id']}"
        elo_ts = latest.get("time", 0)
        if elo_ts:
            dt = datetime.fromtimestamp(elo_ts)
            cr["达成时间"] = {"text": dt.strftime("%Y-%m-%d")}
        result["contest_rating"] = cr

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
# 【模块8：高级功能（Cookie + 抓取 + 解析）】
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
# 【模块9：犇犇（Feed）功能】
# ==============================================

def parse_feed_items(html: str) -> list[dict]:
    """
    解析洛谷主页HTML中的犇犇（feed）列表

    参数：
        html: 主页HTML源码

    返回：
        [{
            "uid": "1157535",
            "username": "yangrenrui",
            "post_id": "142324",        # 可选，犇犇对应的讨论帖ID
            "time": "2026-05-29 21:48:04",
            "feed_id": "15897723",       # 犇犇唯一ID（来自data-report-id）
            "content": "用户标记的输入框处理不对...",
        }, ...]
    """
    items = []

    # 匹配每条犇犇的 am-comment-main 结构
    # 注意：class 属性可能用单引号或双引号，用 (["']) 捕获并 \1 反向引用
    pattern = re.compile(
        r'<div class="am-comment-main">.*?'
        r'<span class="feed-username">'
        r"""<a class=(["'])lg-fg-orange lg-bold\1 href="/user/(\d+)"[^>]*>(.*?)</a>"""
        r'.*?</span>\s*'
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
        r'.*?data-report-id="(\d+)"'
        r'.*?<span class="feed-comment"><p>(.*?)</p></span>',
        re.DOTALL,
    )

    for match in pattern.finditer(html):
        item = {
            "uid": match.group(2),
            "username": match.group(3).strip(),
            "time": match.group(4),
            "feed_id": match.group(5),
            "content": _strip_html(match.group(6)),
        }

        # 提取可选的讨论帖链接
        item_html = match.group(0)
        discuss_match = re.search(r'href="/discuss/show/(\d+)"', item_html)
        if discuss_match:
            item["post_id"] = discuss_match.group(1)

        items.append(item)

    return items


def view_feed() -> dict:
    """
    获取第1页犇犇（第1-10条，需要已登录）

    GET /feed/watching 返回第 1-10 条。

    返回：
        {"code": 200, "data": {
            "items": [...],           # 犇犇列表
            "has_more": True/False,   # 是否满10条（可能还有更多）
            "total": N,               # 本次获取的条数
            "page": 0,                # 当前页（0=首页）
        }}
        或 {"code": 401, "msg": "未登录"}
        或 {"code": 500, "msg": "错误描述"}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        resp = session.get(Config.FEED_WATCHING_URL, headers=Headers.BASE, timeout=10)
        resp.raise_for_status()

        items = parse_feed_items(resp.text)
        total = len(items)

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "items": items,
                "has_more": total >= 10,
                "total": total,
                "page": 0,
            },
        }
    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


def load_more_feed(page: int) -> dict:
    """
    加载指定页的犇犇（需要已登录）

    GET /feed/watching?page=1 返回第 11-20 条，page=2 返回第 21-30 条……

    参数：
        page: 页号（1=第11-20条，2=第21-30条，依此类推）

    返回：
        {"code": 200, "data": {
            "items": [...],
            "has_more": True/False,
            "total": N,
            "page": page,
        }}
        或 {"code": 401, "msg": "未登录"}
        或 {"code": 500, "msg": "错误描述"}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        resp = session.get(
            f"{Config.FEED_WATCHING_URL}?page={page}",
            headers=Headers.BASE,
            timeout=10,
        )
        resp.raise_for_status()

        items = parse_feed_items(resp.text)
        total = len(items)

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "items": items,
                "has_more": total >= 10,
                "total": total,
                "page": page,
            },
        }
    except Exception as e:
        return {"code": 500, "msg": f"加载失败：{str(e)}"}


# ==============================================
# 【模块10：题目功能】
# ==============================================

DIFFICULTY_MAP = {
    0: "暂无评定", 1: "入门", 2: "普及-",
    3: "普及/提高-", 4: "普及+/提高",
    5: "提高+/省选-", 6: "省选/NOI-",
    7: "NOI", 8: "暂不评定",
}


def view_problem(pid: str) -> dict:
    """
    获取并解析洛谷题目（需要已登录）

    参数：
        pid: 题目ID，如 "P1000"

    返回：
        {"code": 200, "data": {
            "pid": "P1000",
            "name": "超级玛丽游戏",
            "difficulty": "入门",
            "totalSubmit": 1775466,
            "totalAccepted": 678862,
            "provider": "洛谷",
            "samples": [["输入1", "输出1"], ...],
            "content": {
                "background": "...",
                "description": "...",
                "formatI": "无",
                "formatO": "如描述。",
                "hint": "...",
            },
        }}
        或 {"code": 401} / {"code": 500}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        resp = session.get(
            f"https://www.luogu.com.cn/problem/{pid}",
            headers=Headers.BASE, timeout=10,
        )
        resp.raise_for_status()

        ctx = _extract_lentille_json(resp.text)
        if not ctx:
            return {"code": 500, "msg": "无法解析题目数据（lentille-context 缺失）"}

        problem = ctx.get("data", {}).get("problem", {})
        if not problem:
            return {"code": 500, "msg": "题目数据为空"}

        content = problem.get("content", {})
        samples = problem.get("samples", [])

        # 将 samples 转为 [["输入","输出"], ...]
        formatted_samples = []
        for s in samples:
            if isinstance(s, list) and len(s) >= 2:
                formatted_samples.append([s[0] or "", s[1] or ""])
            elif isinstance(s, dict):
                formatted_samples.append([s.get("in", ""), s.get("out", "")])

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "pid": problem.get("pid", pid),
                "name": content.get("name") or problem.get("name", ""),
                "difficulty": DIFFICULTY_MAP.get(problem.get("difficulty"), "未知"),
                "totalSubmit": problem.get("totalSubmit", 0),
                "totalAccepted": problem.get("totalAccepted", 0),
                "provider": problem.get("provider", {}).get("name", ""),
                "tags": problem.get("tags", []),
                "samples": formatted_samples,
                "content": {
                    "background": content.get("background", ""),
                    "description": content.get("description", ""),
                    "formatI": content.get("formatI", ""),
                    "formatO": content.get("formatO", ""),
                    "hint": content.get("hint", ""),
                },
            },
        }

    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


def view_discuss(discuss_id: str) -> dict:
    """
    获取并解析洛谷讨论帖（需要已登录）

    参数：
        discuss_id: 讨论ID，如 "962230"

    返回：
        {"code": 200, "data": {
            "id": 962230,
            "title": "求助站外题颜色评级",
            "author": "hansang",
            "author_uid": 723888,
            "time": "2024-10-16 19:33",
            "forum": "灌水区",
            "replyCount": 2,
            "content": "[题目链接]...",   # Markdown 格式
        }}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        resp = session.get(
            f"https://www.luogu.com.cn/discuss/{discuss_id}",
            headers=Headers.BASE, timeout=10,
        )
        resp.raise_for_status()

        ctx = _extract_lentille_json(resp.text)
        if not ctx:
            return {"code": 500, "msg": "无法解析讨论数据"}

        post = ctx.get("data", {}).get("post", {})
        if not post:
            return {"code": 500, "msg": "讨论数据为空"}

        author = post.get("author", {})
        ts = post.get("time", 0)
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "id": post.get("id"),
                "title": post.get("title", ""),
                "author": author.get("name", ""),
                "author_uid": author.get("uid", ""),
                "time": time_str,
                "forum": post.get("forum", {}).get("name", ""),
                "replyCount": post.get("replyCount", 0),
                "content": post.get("content", ""),
            },
        }

    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


# ==============================================
# 【模块11：讨论列表功能】
# ==============================================

DISCUSS_LIST_URL = "https://www.luogu.com.cn/discuss"


def parse_discuss_list(html: str) -> list[dict]:
    """
    从 lentille-context JSON 解析讨论列表

    返回：
        [{
            "uid": "2031506",
            "username": "gcx20121216",
            "discuss_id": "1300939",
            "title": "请求大神",
            "time": "2026-06-01 19:31:51",
            "forum": "B2092 开关灯",
            "replyCount": 5,
            "topped": False,
        }, ...]
    """
    ctx = _extract_lentille_json(html)
    if not ctx:
        return []

    posts = ctx.get("data", {}).get("posts", {})
    result = posts.get("result", [])
    if not result:
        return []

    items = []
    for post in result:
        author = post.get("author", {})
        ts = post.get("time", 0)
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
        forum = post.get("forum", {})

        items.append({
            "uid": str(author.get("uid", "")),
            "username": author.get("name", ""),
            "discuss_id": str(post.get("id", "")),
            "title": post.get("title", ""),
            "time": time_str,
            "forum": forum.get("name", ""),
            "replyCount": post.get("replyCount", 0),
            "topped": post.get("topped", False),
        })

    return items


def view_discuss_list(page: int = 1) -> dict:
    """
    获取并解析讨论列表（需要已登录）

    参数：
        page: 页号（1-20，1 为第1页）

    返回：
        {"code": 200, "data": {
            "items": [...],
            "page": page,
            "total": N,
        }}
        或 {"code": 401} / {"code": 500}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        url = DISCUSS_LIST_URL if page <= 1 else f"{DISCUSS_LIST_URL}?page={page}"
        resp = session.get(url, headers=Headers.BASE, timeout=10)
        resp.raise_for_status()

        items = parse_discuss_list(resp.text)

        # 从 lentille-context 获取分页信息
        ctx = _extract_lentille_json(resp.text)
        per_page = 30
        total_count = 0
        if ctx:
            posts = ctx.get("data", {}).get("posts", {})
            per_page = posts.get("perPage", 30)
            total_count = posts.get("count", 0)

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "items": items,
                "page": page,
                "perPage": per_page,
                "totalCount": total_count,
                "total": len(items),
            },
        }
    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


def view_article(article_id: str) -> dict:
    """
    获取并解析洛谷文章（需要已登录）

    参数：
        article_id: 文章ID，如 "qzywo77y"

    返回：
        {"code": 200, "data": {
            "id": "qzywo77y",
            "title": "浅谈公平组合游戏",
            "author": "Moya_Rao",
            "author_uid": 814130,
            "time": "2026-05-29 12:33",
            "upvote": 105,
            "replyCount": 73,
            "category": "题解",
            "content": "本文同步发表在...",  # Markdown 格式
        }}
    """
    CATEGORY_MAP = {0: "其他", 1: "题解", 2: "技术", 3: "游记", 4: "分享", 5: "闲话"}

    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        resp = session.get(
            f"https://www.luogu.com.cn/article/{article_id}",
            headers=Headers.BASE, timeout=30,
        )
        resp.raise_for_status()

        ctx = _extract_lentille_json(resp.text)
        if not ctx:
            return {"code": 500, "msg": "无法解析文章数据"}

        article = ctx.get("data", {}).get("article", {})
        if not article:
            return {"code": 500, "msg": "文章数据为空"}

        author = article.get("author", {})
        ts = article.get("time", 0)
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
        cat = article.get("category", 0)

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "id": article.get("lid", article_id),
                "title": article.get("title", ""),
                "author": author.get("name", ""),
                "author_uid": author.get("uid", ""),
                "time": time_str,
                "upvote": article.get("upvote", 0),
                "replyCount": article.get("replyCount", 0),
                "favorCount": article.get("favorCount", 0),
                "category": CATEGORY_MAP.get(cat, f"未知({cat})"),
                "content": article.get("content", ""),
            },
        }

    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


# ==============================================
# 【模块12：文章列表功能】
# ==============================================

ARTICLE_LIST_URL = "https://www.luogu.com.cn/article"

CATEGORY_NAMES = {0: "其他", 1: "题解", 2: "技术", 3: "游记", 4: "分享", 5: "闲话"}


def parse_article_list(html: str) -> list[dict]:
    """
    从 lentille-context JSON 解析文章列表

    返回：
        [{
            "lid": "qzywo77y",
            "title": "浅谈公平组合游戏",
            "category": "分享",
            "time": "2026-05-29 12:33",
            "author_uid": "814130",
            "author": "Moya_Rao",
            "upvote": 134,
            "replyCount": 86,
        }, ...]
    """
    ctx = _extract_lentille_json(html)
    if not ctx:
        return []

    articles = ctx.get("data", {}).get("articles", {})
    result = articles.get("result", [])
    if not result:
        return []

    items = []
    for a in result:
        author = a.get("author", {})
        ts = a.get("time", 0)
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
        cat = a.get("category", 0)

        items.append({
            "lid": a.get("lid", ""),
            "title": a.get("title", ""),
            "category": CATEGORY_NAMES.get(cat, f"未知({cat})"),
            "time": time_str,
            "author_uid": str(author.get("uid", "")),
            "author": author.get("name", ""),
            "upvote": a.get("upvote", 0),
            "replyCount": a.get("replyCount", 0),
        })

    return items


def view_article_list(page: int = 1) -> dict:
    """
    获取并解析文章列表（需要已登录）

    参数：
        page: 页号（1-30，1 为第1页）

    返回：
        {"code": 200, "data": {
            "items": [...],
            "page": page,
            "perPage": 15,
            "totalCount": 450,
        }}
    """
    session = load_cookie()
    if not session:
        return {"code": 401, "msg": "未登录，请先执行 login"}

    try:
        url = ARTICLE_LIST_URL if page <= 1 else f"{ARTICLE_LIST_URL}?page={page}"
        resp = session.get(url, headers=Headers.BASE, timeout=10)
        resp.raise_for_status()

        items = parse_article_list(resp.text)

        # 分页信息
        ctx = _extract_lentille_json(resp.text)
        per_page = 15
        total_count = 0
        if ctx:
            articles = ctx.get("data", {}).get("articles", {})
            per_page = articles.get("perPage", 15)
            total_count = articles.get("count", 0)

        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "items": items,
                "page": page,
                "perPage": per_page,
                "totalCount": total_count,
                "total": len(items),
            },
        }
    except Exception as e:
        return {"code": 500, "msg": f"获取失败：{str(e)}"}


# ==============================================
# 【模块13：CLI 命令行入口】
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

    # profile 子命令
    profile_p = subparsers.add_parser("profile", help="查看用户资料")
    profile_p.add_argument("--url", help="用户主页地址（留空使用默认）")

    # home 子命令
    subparsers.add_parser("home", help="查看主页运势/动态")

    # logout 子命令
    subparsers.add_parser("logout", help="清除本地 Cookie（注销）")

    # feed 子命令
    feed_p = subparsers.add_parser("feed", help="查看犇犇动态")
    feed_p.add_argument(
        "--page", type=int, default=None,
        help="指定页号（1=第11-20条，2=第21-30条……；省略=第1-10条）",
    )

    # problem 子命令
    problem_p = subparsers.add_parser("problem", help="查看题目预览")
    problem_p.add_argument("pid", help="题目ID，如 P1000")

    # discuss 子命令
    discuss_p = subparsers.add_parser("discuss", help="查看讨论帖")
    discuss_p.add_argument("did", help="讨论ID，如 962230")

    # article 子命令
    article_p = subparsers.add_parser("article", help="查看文章")
    article_p.add_argument("aid", help="文章ID，如 qzywo77y")

    args = parser.parse_args()

    # ---- 命令分发 ----
    if args.command == "login":
        password = _resolve_password(args)
        result = login(args.user, password)
        # 清除本地变量中的密码
        password = ""
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

    elif args.command == "feed":
        if args.page is not None:
            result = load_more_feed(args.page)
        else:
            result = view_feed()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "problem":
        result = view_problem(args.pid)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "discuss":
        result = view_discuss(args.did)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "article":
        result = view_article(args.aid)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(json.dumps({"code": 50001}, ensure_ascii=False))


if __name__ == "__main__":
    main()
