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

# ==============================================
# 【模块2：请求头】
# ==============================================
class Headers:
    BASE = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": Config.LOGIN_PAGE,
    }

# ==============================================
# 【模块3：刷新C3VK Cookie】
# ==============================================
def refresh_c3vk(session: requests.Session) -> bool:
    try:
        session.get(Config.C3VK_REFRESH_URL, headers=Headers.BASE, allow_redirects=True, timeout=5)
        return True
    except:
        return False

# ==============================================
# 【模块4：Cookie 保存/加载】
# ==============================================
def save_cookie(session: requests.Session) -> dict:
    try:
        cookies = session.cookies.get_dict()
        with open(Config.COOKIE_SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False)
        return {"status": True, "data": cookies}
    except Exception as e:
        return {"status": False, "msg": str(e)}

def load_cookie() -> requests.Session | None:
    if not os.path.exists(Config.COOKIE_SAVE_PATH):
        return None
    session = requests.Session()
    with open(Config.COOKIE_SAVE_PATH, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    for k, v in cookies.items():
        session.cookies.set(k, v)
    refresh_c3vk(session)
    return session

# ==============================================
# 【模块5：验证码下载+OCR识别】
# ==============================================
def get_captcha(session: requests.Session) -> dict:
    try:
        if os.path.exists(Config.CAPTCHA_PATH):
            os.remove(Config.CAPTCHA_PATH)
        
        time.sleep(random.uniform(1, 1.5))
        timestamp = f"{time.time() * 1000}.{random.randint(100, 999)}"
        resp = session.get(f"{Config.CAPTCHA_API}?_t={timestamp}", headers=Headers.BASE, timeout=10)
        resp.raise_for_status()
        
        with open(Config.CAPTCHA_PATH, "wb") as f:
            f.write(resp.content)
        
        with open(Config.CAPTCHA_PATH, "rb") as f:
            img_base64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
        ocr_res = requests.post(Config.OCR_API, json={"image": img_base64}, timeout=10).json()
        
        captcha = str(ocr_res.get("data", "")).strip().upper()
        if len(captcha) == 4:
            return {"status": True, "code": captcha}
        return {"status": False, "msg": "格式错误"}
    except Exception as e:
        return {"status": False, "msg": str(e)}
    finally:
        if os.path.exists(Config.CAPTCHA_PATH):
            os.remove(Config.CAPTCHA_PATH)

# ==============================================
# 【模块6：登录功能（验证码自动重试）】
# ==============================================
def luogu_login(user: str, pwd: str) -> str:
    session = requests.Session()
    try:
        resp = session.get(Config.LOGIN_PAGE, headers=Headers.BASE, timeout=10)
        csrf = re.search(r'<meta name="csrf-token" content="(.*?)">', resp.text).group(1)
        
        refresh_c3vk(session)

        captcha = ""
        for _ in range(Config.MAX_CAPTCHA_RETRY):
            cap_res = get_captcha(session)
            if cap_res["status"]:
                captcha = cap_res["code"]
                break
        
        if not captcha:
            return json.dumps({"code": 500, "msg": "验证码获取失败"}, ensure_ascii=False)

        login_headers = {
            **Headers.BASE,
            "Content-Type": "application/json",
            "Origin": "https://www.luogu.com.cn",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf
        }

        login_data = {"username": user, "password": pwd, "captcha": captcha}
        for _ in range(Config.MAX_CAPTCHA_RETRY):
            resp = session.post(Config.LOGIN_API, json=login_data, headers=login_headers, allow_redirects=False, timeout=10)
            if resp.status_code == 200:
                break
            cap_res = get_captcha(session)
            if cap_res["status"]:
                login_data["captcha"] = cap_res["code"]

        if resp.status_code != 200:
            return json.dumps({"code": 400, "msg": "登录失败（账号/密码/验证码错误）"}, ensure_ascii=False)

        save_cookie(session)
        return json.dumps({"code": 200, "msg": "登录成功", "cookies": session.cookies.get_dict()}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"code": 500, "msg": f"服务器错误：{str(e)}"}, ensure_ascii=False)

# ==============================================
# 【模块7：页面访问功能】
# ==============================================
def view_page(url: str = None) -> str:
    session = load_cookie()
    if not session:
        return json.dumps({"code": 401, "msg": "未登录，请先执行login"}, ensure_ascii=False)
    
    target = url or Config.DEFAULT_VIEW_URL
    try:
        resp = session.get(target, headers=Headers.BASE, timeout=10)
        resp.raise_for_status()
        return json.dumps({
            "code": 200,
            "msg": "访问成功",
            "url": target,
            "html": resp.text,
            "cookies": session.cookies.get_dict()
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 500, "msg": f"访问失败：{str(e)}"}, ensure_ascii=False)

# ==============================================
# 【模块8：命令行入口】命令错误返回50001
# ==============================================
def main():
    parser = argparse.ArgumentParser(description="server")
    def err_handle(msg):
        print(json.dumps({"code": 50001}, ensure_ascii=False))
        exit()
    parser.error = err_handle

    subparsers = parser.add_subparsers(dest="command", required=True)

    login_p = subparsers.add_parser("login")
    login_p.add_argument("--user", required=True)
    login_p.add_argument("--pwd", required=True)

    view_p = subparsers.add_parser("view")
    view_p.add_argument("--url", help="自定义访问地址")

    args = parser.parse_args()

    if args.command == "login":
        print(luogu_login(args.user, args.pwd))
    elif args.command == "view":
        print(view_page(args.url))
    else:
        print(json.dumps({"code": 50001}, ensure_ascii=False))

if __name__ == "__main__":
    main()