// ==UserScript==
// @name         洛谷私信本地通知
// @namespace    https://github.com/liangbinchen
// @version      1.0
// @author       liangbinchen
// @match        https://www.luogu.com.cn/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function () {
    'use strict';
    let chatWSRD = false;

    function getCurrentUserId() {
        let login = document.querySelector("[href='/auth/login']");
        if (login) return null;
        let avatarImg = document.querySelector("img.avatar[data-v-0a5f98b2]");
        if (!avatarImg) {
            avatarImg = document.querySelector(".user-nav .avatar img[data-v-65720dbc]");
        }
        if (avatarImg && avatarImg.src) {
            const match = avatarImg.src.match(/\/upload\/usericon\/(\d+)\.png/);
            if (match) return match[1];
        }
        return null;
    }

    function sendLocal(obj) {
        GM_xmlhttpRequest({
            method: "POST",
            url: "http://127.0.0.1:8888/send",
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify(obj)
        });
    }

    function startWS() {
        const myUid = getCurrentUserId();
        if (!myUid || chatWSRD) return;
        chatWSRD = true;

        const ws = new WebSocket("wss://ws.luogu.com.cn/ws");
        ws.onopen = () => {
            ws.send(JSON.stringify({
                channel: "chat",
                channel_param: myUid,
                type: "join_channel"
            }));
        };

        ws.onmessage = e => {
            const d = JSON.parse(e.data);
            if (d._ws_type !== "server_broadcast") return;
            const msg = d.message;
            if (!msg || msg.sender.uid == myUid) return;

            const payload = {
                User: msg.sender.name,
                UID: String(msg.sender.uid),
                Time: new Date().toLocaleString(),
                Content: msg.content
            };
            sendLocal(payload);
        };
    }

    setTimeout(startWS, 1200);
})();
