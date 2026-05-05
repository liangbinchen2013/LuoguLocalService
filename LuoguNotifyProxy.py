from flask import Flask, request
import socket
import json

app = Flask(__name__)

TCP_HOST = "127.0.0.1"
TCP_PORT = 16666
LISTEN_PORT = 8888

def send_to_tcp(json_str):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TCP_HOST, TCP_PORT))
        sock.sendall(json_str.encode("utf-8"))
        sock.close()
    except Exception:
        pass

@app.route("/send", methods=["POST"])
def send():
    try:
        data = request.get_json()
        send_to_tcp(json.dumps(data, ensure_ascii=False))
        return {"code": 0}, 200
    except Exception:
        return {"code": -1}, 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=LISTEN_PORT, debug=False)