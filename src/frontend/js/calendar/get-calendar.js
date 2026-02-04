
'use strict';
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
import { escapeHtml } from './escape.js';

let idToken = null;

document.addEventListener("DOMContentLoaded", async () => {

    // ログインしていなければ終了
    idToken = localStorage.getItem("idToken");
    console.log(`idToken: ${idToken}`)

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
    console.log("Refreshed Token successfully")
    localStorage.setItem("idToken", refreshRes.AuthenticationResult.IdToken);
    localStorage.setItem("accessToken", refreshRes.AuthenticationResult.AccessToken);
    idToken = refreshRes.AuthenticationResult.IdToken;
  
    // デフォルトで今日の日付と31日後の日付をフォームにセット
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;

    document.getElementById("start_date").value = todayStr;

    const endDate = new Date(today);
    endDate.setDate(today.getDate() + 31);
    const endStr = `${endDate.getFullYear()}-${String(endDate.getMonth()+1).padStart(2,'0')}-${String(endDate.getDate()).padStart(2,'0')}`;
    document.getElementById("end_date").value = endStr;

    // カレンダー表示関数を直接呼び出す
    await displayCalendar();
});

// カレンダー表示
async function displayCalendar(){
    const start_date = document.getElementById("start_date").value;
    const end_date = document.getElementById("end_date").value;
    const apiGatewayBaseUrl = API_GATEWAY_URL;

    if (end_date < start_date) {
        alert("終了日は、開始日より後の日付にしてください");
        return;
    }

    let response;
    try {
        response = await fetch(`${apiGatewayBaseUrl}/get-calendar?start_date=${encodeURIComponent(start_date)}&end_date=${encodeURIComponent(end_date)}`,{
            method: "GET",
            headers: {
                "Content-Type":"application/json", 
                "Authorization": idToken
            },
        });

        if (!response.ok){
            throw new Error(`HTTP error: ${response.status}`)
        }
        
    } catch(error) {
        console.log(error);
        document.getElementById("section1").innerHTML = "<p>データが取得できませんでした</p>";
        return;
    }

    const bodyJson = await response.json();
    if (bodyJson.status === "success"){
        document.getElementById("nameplate").innerHTML = `<p>${escapeHtml(bodyJson.message.username)}さん、ログイン中</p>`
        // console.log(bodyJson.message.data);
        create_rows(bodyJson.message.data);
    } else {
        document.getElementById("section1").innerHTML = "<p>データが取得できませんでした</p>";
    }
}

// カレンダーの行を作成する関数
function create_rows(data){
    const apiBaseUrl = "get-detail.html?date=";
    let resultHtml = "<table><tr>";
    resultHtml += "<th>日付</th><th>曜日</th><th>祝日</th><th>予定</th></tr>";
    for (const row of data){
        let style = "";
        // 土日の場合、色を変える
        if (row.weekday === "土"){ 
            style = 'style="color: blue;"'; 
        } 
        if (row.weekday === "日"){
                style = 'style="color: red;"'; 
        }
        // 祝日の場合、色を変える
        if (row.holiday_name){
            style = 'style="color: red;"';
        }
        // 日付の行をクリックしたとき、その日のページへ移動

               resultHtml += `<tr onclick="location.href='${apiBaseUrl}${escapeHtml(row.date)}'" style="cursor:pointer;">`; resultHtml += `<td ${style}>${escapeHtml(row.date)}</td>`;
        resultHtml += `<td ${style}>${escapeHtml(row.weekday)}</td>`;
        resultHtml += `<td ${style}>${escapeHtml(row.holiday_name)}</td>`;
        // 予定欄は色をつけない
        resultHtml += `<td>${escapeHtml(row.events)}</td>`;
        resultHtml += '</tr>';
    }
    resultHtml += "</table>";
    document.getElementById("section1").innerHTML = resultHtml;
}

// フォームのsubmitが行なわれたとき
document.getElementById("myForm").addEventListener("submit", (e) => {
    e.preventDefault();
    displayCalendar();
});

// パスワード変更ボタンをクリックしたとき
document.getElementById("changePasswordBtn").addEventListener("click", () =>{
    window.location.href = "change-password.html";
})
