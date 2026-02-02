"use strict";
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
// HTMLエスケープ関数（XSS対策）
import { escapeHtml } from './escape.js';

let idToken = "";

document.addEventListener("DOMContentLoaded", async function(){

    // idTokenの更新処理
    const refreshRes = await refreshCognitoToken();
    console.log(refreshRes);
    if (refreshRes.AuthenticationResult){
        console.log("Refreshed Token successfully")
        localStorage.setItem("idToken", refreshRes.AuthenticationResult.idToken);
        localStorage.setItem("accessToken", refreshRes.AuthenticationResult.AccessToken);

        idToken = refreshRes.AuthenticationResult.IdToken;

    } else {
        window.alert("トークンの更新に失敗しました");
        window.location.href = "index.html";
        return;
    }

    // ログインしている場合は、日付をセットする
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

document.getElementById("myForm").addEventListener("submit",function(e){
    e.preventDefault();

    const postData = {
    date: document.getElementById("date").value,
    event_name: document.getElementById("event_name").value,
    event_detail: document.getElementById("event_detail").value
    };

    const apiGatewayBaseUrl = API_GATEWAY_URL;
    fetch(`${apiGatewayBaseUrl}/add-event`,{
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": idToken
        },
        body: JSON.stringify(postData)
    })
    .then(body => body.json())
    .then(bodyJson => {
    if (bodyJson.status === "success"){
        const date = document.getElementById("date").value;
        window.location.href = `get-detail.html?date=${encodeURIComponent(date)}`;
        // window.location.href = "get-calendar.html";
    } else {
        const resultMessage = document.getElementById("resultArea");
        resultMessage.innerHTML = `<p>エラーが発生しました：${escapeHtml(bodyJson.message)}</p>`;
        console.log(bodyJson);
    }
    });
});