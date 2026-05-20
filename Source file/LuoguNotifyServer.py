import socket
import json
import time
from win10toast import ToastNotifier

HOST = '127.0.0.1'
PORT = 16666
NOTIFICATION_DURATION = 5

toaster = ToastNotifier()

def show_notify(title, msg):
    try:
        # 关键修复：threaded 必须关掉！
        toaster.show_toast(
            title=title,
            msg=msg,
            duration=NOTIFICATION_DURATION,
            threaded=False
        )
    except Exception as e:
        print("通知错误:", e)

def start_listen():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print("TCP 服务已启动：127.0.0.1:16666")

    while True:
        conn, _ = server.accept()
        try:
            data = conn.recv(2048).decode("utf-8").strip()
            if not data:
                continue

            print("收到数据：", data)

            d = json.loads(data)
            user = d.get("User", "未知用户")
            content = d.get("Content", "无内容")

            print(f"弹出通知：{user} -> {content}")
            show_notify(f"洛谷私信 · {user}", content)

        except Exception as e:
            print("解析错误：", e)
        finally:
            conn.close()

if __name__ == "__main__":
    start_listen()
