"use strict";
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
let idToken = ""

document.addEventListener("DOMContentLoaded", async function(){
    try {
    // idTokenの更新処理
    const refreshRes = await refreshCognitoToken();
    console.log(refreshRes);
    if (refreshRes.AuthenticationResult){
        console.log("Refreshed Token successfully")
        localStorage.setItem("idToken", refreshRes.AuthenticationResult.IdToken);
        localStorage.setItem("accessToken", refreshRes.AuthenticationResult.AccessToken);

        idToken = refreshRes.AuthenticationResult.IdToken;

    } else {
        window.alert("トークンの更新に失敗しました");
        window.location.href = "index.html";
        return;
    }

    // ログインされている場合、下記を実行
    // URLからGETパラメータを取得
    const params = new URLSearchParams(window.location.search);
    const event_id = params.get("event_id");
    const apiGatewaBaseUrl = API_GATEWAY_URL;
    const apiUrl = `${apiGatewaBaseUrl}/get-event?event_id=${encodeURIComponent(event_id)}`;

    fetch(apiUrl,{
        method: "GET",
        headers: {
            "authorization": idToken
        }
    })
    .then(body => body.json())
    // .then(resJson => JSON.parse(resJson.body))
    .then(bodyJson => {
        if (bodyJson.status === "success") {
        document.getElementById("nameplate").innerHTML = `<p>${bodyJson.message.username}さん、ログイン中</p>`;
        document.getElementById("event_id").value = bodyJson.message.data.event_id;
        document.getElementById("date").value = bodyJson.message.data.date;
        document.getElementById("event_name").value = bodyJson.message.data.event_name;
        document.getElementById("event_detail").value = bodyJson.message.data.event_detail;
        } else {
        window.alert("データの取得に失敗しました");
        console.log(bodyJson);
        window.location.href = "get-calendar.html";
        }
    });
    } catch (error) {
        window.alert("データの取得に失敗しました");
        console.log(error)
        window.location.href = "get-calendar.html";
    }
});

document.getElementById("myForm").addEventListener("submit",function(e){
    e.preventDefault();

    // ログイン判定
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
    fetch(`${apiGatewayBaseUrl}/update-event`,{
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "authorization": idToken
    },
    body: JSON.stringify(postData)
    })
    .then(body => body.json())
    // .then(resJson => JSON.parse(resJson.body))
    .then(bodyJson => {
    if (bodyJson.status === "success"){
        // window.alert("更新に成功しました")
        window.location.href = "get-calendar.html";
    } else {
        window.alert("更新に失敗しました");
        // window.location.href = "get-calendar.html";
    }
    })
    .catch(error =>{
        console.log(error);
        window.alert("更新に失敗しました");
        window.location.href = "get-calendar.html"; 
    });
});