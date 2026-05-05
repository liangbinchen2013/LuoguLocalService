import socket
import json
from win10toast import ToastNotifier

HOST = '127.0.0.1'
PORT = 16666
NOTIFICATION_DURATION = 5

toaster = ToastNotifier()

def show_notify(title, msg):
    try:
        toaster.show_toast(
            title=title,
            msg=msg,
            duration=NOTIFICATION_DURATION,
            threaded=True
        )
    except Exception:
        pass

def start_listen():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    while True:
        conn, _ = server.accept()
        try:
            data = conn.recv(2048).decode("utf-8").strip()
            if not data:
                continue

            d = json.loads(data)
            user = d.get("User", "未知用户")
            content = d.get("Content", "")

            show_notify(f"洛谷私信 · {user}", content)
        except Exception:
            pass
        finally:
            conn.close()

if __name__ == "__main__":
    start_listen()