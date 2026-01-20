
'use strict';
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
let idToken = null;

document.addEventListener("DOMContentLoaded", async function() {
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

    // 以下は、ログインに問題ない場合に実行
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
    // ページを開いたときに、強制的にPOSTする
    document.getElementById("myForm").dispatchEvent(new Event("submit"));
});

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
        resultHtml += `<tr onclick="location.href='${apiBaseUrl}${row.date}'" style="cursor:pointer;">`;
        resultHtml += `<td ${style}>${row.date}</td>`;
        resultHtml += `<td ${style}>${row.weekday}</td>`;
        resultHtml += `<td ${style}>${row.holiday_name === null ? "" : row.holiday_name}</td>`;
        // 予定欄は色をつけない
        resultHtml += `<td>${row.events === null ? "" : row.events}</td>`;
        resultHtml += '</tr>';
    }
    resultHtml += "</table>";
    document.getElementById("section1").innerHTML = resultHtml;
}
// フォームのsubmitが押されたとき
document.getElementById("myForm").addEventListener("submit", function(e){
    e.preventDefault();

    const start_date = document.getElementById("start_date").value;
    const end_date = document.getElementById("end_date").value;
    const apiGatewayBaseUrl = API_GATEWAY_URL;

    if (end_date < start_date) {
        alert("終了日は、開始日より後の日付にしてください");
        return;
    }

    fetch(`${apiGatewayBaseUrl}/get-calendar?start_date=${encodeURIComponent(start_date)}&end_date=${encodeURIComponent(end_date)}`,{
    method: "GET",
    headers: {
        "Content-Type":"application/json", 
        "Authorization": idToken
    },
    })
    .then(body => body.json())
    .then(bodyJson => {
    if (bodyJson.status === "success"){
        document.getElementById("nameplate").innerHTML = `<p>${bodyJson.message.username}さん、ログイン中</p>`
        // console.log(bodyJson.message.data);
        create_rows(bodyJson.message.data);
    } else {
        document.getElementById("section1").innerHTML = "<p>データが取得できませんでした</p>";
    }
    })
    .catch(error => {
        console.log(error);
        document.getElementById("section1").innerHTML = "<p>データが取得できませんでした</p>";
    });
});

// パスワード変更ボタン
document.getElementById("changePasswordBtn").addEventListener("click",function(){
    window.location.href = "change-password.html";
    return;
})
