"use strict";
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
// HTMLエスケープ関数（XSS対策）
import { escapeHtml } from './escape.js';

let idToken = "";

// page表示時の処理
document.addEventListener("DOMContentLoaded", async () => {

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

    // URLからGETパラメータを取得
    const params = new URLSearchParams(window.location.search);
    const event_id = params.get("event_id");
    const apiGatewayBaseUrl = API_GATEWAY_URL;
    const apiUrl = `${apiGatewayBaseUrl}/get-event?event_id=${encodeURIComponent(event_id)}`;

    let response;
    try {
        response = await fetch(apiUrl,{
            method: "GET",
            headers: {
                "authorization": idToken
            }
        });

        if (!response.ok){
            throw new Error(`HTTP error: ${response.status}`);
        }
    } catch (error) {
        window.alert("データの取得に失敗しました");
        console.log(error);
        window.location.href = "get-calendar.html";
        return;
    }

    const bodyJson = await response.json();
    if (bodyJson.status === "success") {
        // データが取得できた場合は、フォームのデフォルト値に取得データを入れる
        document.getElementById("nameplate").innerHTML = `<p>${escapeHtml(bodyJson.message.username)}さん、ログイン中</p>`;
        document.getElementById("event_id").value = bodyJson.message.data.event_id;
        document.getElementById("date").value = bodyJson.message.data.date;
        document.getElementById("event_name").value = bodyJson.message.data.event_name;
        document.getElementById("event_detail").value = bodyJson.message.data.event_detail;
        // 戻るボタンのリンク先を日付のページに設定
        document.getElementById("backButton").onclick = function() {
            const date = bodyJson.message.data.date;
            window.location.href = `get-detail.html?date=${encodeURIComponent(date)}`;
        };
    } else {
        window.alert("データの取得に失敗しました");
        console.log(bodyJson);
        window.location.href = "get-calendar.html";
    }


});

// submitが押された場合
document.getElementById("myForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    // ログイン判定（実用上、idTokenの更新処理はしない）
    idToken = localStorage.getItem("idToken");
    if (!idToken){
        window.alert("ログインしていません");
        window.location.href = "index.html";
        return;
    }

    const postData = {
        event_id: document.getElementById("event_id").value,
        date: document.getElementById("date").value,
        event_name: document.getElementById("event_name").value,
        event_detail: document.getElementById("event_detail").value
    };

    const apiGatewayBaseUrl = API_GATEWAY_URL;
    // 入力値をPOSTする
    let response;
    try {
        response = await fetch(`${apiGatewayBaseUrl}/update-event`,{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "authorization": idToken
            },
            body: JSON.stringify(postData)
        });

        if (!response.ok){
            throw new Error(`HTTP error: ${response.status}`);
        }
    } catch (error){
        console.error("予定情報の更新でエラー発生：", error);
        window.alert("更新に失敗しました");
        window.location.href = "get-calendar.html"; 
        return;
    }

    const bodyJson = await response.json();
    if (bodyJson.status === "success"){
        // POST成功の場合、その日の予定一覧に移動
        const date = document.getElementById("date").value;
        window.location.href = `get-detail.html?date=${encodeURIComponent(date)}`;
    } else {
        window.alert("更新に失敗しました");
        // console.log(bodyJson);
    }
});