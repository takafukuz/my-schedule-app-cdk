"use strict";
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
// HTMLエスケープ関数（XSS対策）
import { escapeHtml } from './escape.js';

let idToken = "";

document.addEventListener("DOMContentLoaded", async () =>{

    // ログインしていなければ終了
    idToken = localStorage.getItem("idToken");
    console.log(`idToken: ${idToken}`);

    if (!idToken){
        window.alert("ログインしていません");
        window.location.href = "index.html";
        return;
    }

    // idTokenの更新処理
    const refreshRes = await refreshCognitoToken();

    if (refreshRes.status === "error"){
        window.alert("トークンの更新に失敗: " + refreshRes.message);
        window.location.href = "index.html";
        return;
    }

    if (!refreshRes.AuthenticationResult){
        window.alert("トークンの更新に失敗：AuthenticationResultがありません");
        window.location.href = "index.html";
        return;
    }

    // 以下、トークン更新成功時に実行
    console.log("Refreshed Token successfully");
    localStorage.setItem("idToken", refreshRes.AuthenticationResult.IdToken);
    localStorage.setItem("accessToken", refreshRes.AuthenticationResult.AccessToken);
    idToken = refreshRes.AuthenticationResult.IdToken;

    // 日付をセットする
    const getParams = new window.URLSearchParams(window.location.search);
    const date = getParams.get("date");
    if (date){
        document.getElementById("date").value = date;
    } else {
        const today = new Date();
        const yyyy = String(today.getFullYear());
        const mm = String(today.getMonth()+1).padStart(2,"0");
        const dd = String(today.getDate()).padStart(2,"0");
        document.getElementById("date").value = `${yyyy}-${mm}-${dd}`;
    }
});

// submitポタンクリック時の処理
document.getElementById("myForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    // ログインしていなければ終了（実用上、idTokenの更新処理はしない）
    idToken = localStorage.getItem("idToken");
    console.log(`idToken: ${idToken}`);

    if (!idToken){
        window.alert("ログインしていません");
        window.location.href = "index.html";
        return;
    }

    // 予定追加処理の実行
    const postData = {
        date: document.getElementById("date").value,
        event_name: document.getElementById("event_name").value,
        event_detail: document.getElementById("event_detail").value
    };

    const apiGatewayBaseUrl = API_GATEWAY_URL;

    let response;
    try {
        response = await fetch(`${apiGatewayBaseUrl}/add-event`,{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": idToken
            },
            body: JSON.stringify(postData)
        });

        if (!response.ok){
            throw new Error(`HTTP error: ${response.status}`);
        }
    } catch (error) {
        console.error("予定の追加時にエラー発生", error);
        window.alert("予定の追加時にエラー発生");
        return;
    }

    const bodyJson = await response.json();
    if (bodyJson.status === "success"){
        // 登録成功の場合、その日の予定一覧画面に遷移
        const date = document.getElementById("date").value;
        window.location.href = `get-detail.html?date=${encodeURIComponent(date)}`;
    } else {
        console.error("予定の追加時にエラー発生",bodyJson);
        window.alert("予定の追加時にエラー発生");
    }
});