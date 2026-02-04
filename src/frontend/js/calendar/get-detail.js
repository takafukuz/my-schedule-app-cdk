'use strict';
import { API_GATEWAY_URL } from '../config/api-gateway-config.js';
import { escapeHtml } from './escape.js';

let idToken = "";

// GETパラメータの取得
const params = new URLSearchParams(window.location.search);
const date = params.get("date");

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

    const apiGatewayBaseUrl = API_GATEWAY_URL;
    const apiUrl = `${apiGatewayBaseUrl}/get-detail?date=${encodeURIComponent(date)}`;

    document.getElementById("subTitle").innerHTML = `${escapeHtml(date)}の予定`;
    // 当該日の予定をAPIから取得して、テーブルで表示
    try {
        const response = await fetch(apiUrl,{
            method: "GET",
            headers: {
                // "Content-Type":"application/json", //GETのときにContent-Typeは不要
                "Authorization": idToken
            }
        });

        if (!response.ok){
            throw new Error(`HTTP error: ${response.status}`);
        }

        const bodyJson = await response.json();
        if (bodyJson.status === "success"){
            // console.log("success")
            console.log(bodyJson);
            // console.log(bodyJson.message);
            document.getElementById("nameplate").innerHTML = `<p>${escapeHtml(bodyJson.message.username)}さん、ログイン中</p>`;
            // データが空の場合
            if (!bodyJson.message.data || Object.keys(bodyJson.message.data).length === 0) {
                document.getElementById("resultArea").innerHTML =
                    `<p style="color:red; text-align:center;">予定がありません</p>`;
                return; // これ以上処理しない
            }
            // データがある場合は、テーブルを作成する
            create_table(bodyJson.message.data);
        } else {
            console.log(bodyJson);
            document.getElementById("resultArea").innerText = "データが取得できませんでした";
        }
    } catch(error) {
        console.log(error);
        document.getElementById("resultArea").innerText = "データが取得できませんでした";
    }

});

function create_table(data){
    const baseApiUrl = "edit-event.html?event_id=";
    let resultHtml = '<form id="myForm">';
    resultHtml += '<table><tr>';
    resultHtml += "<th>選択</th><th>予定番号</th><th>日付</th><th>予定名</th><th>予定詳細</th></tr>";

    for (const row of data){
        // 行をクリックしたら、その予定の編集画面に遷移
        resultHtml += `<tr onclick="location.href='${baseApiUrl}${escapeHtml(row.event_id)}'" style="cursor:pointer;">`;
        for (const key in row){
            let word = row[key] || "";
            if (key === "event_id"){
                // 削除用チェックボックスは、行のクリックイベントを阻止
                resultHtml += `<td><input type="checkbox" name="selectedEvent" value="${escapeHtml(word)}" onclick="event.stopPropagation();"></td>`;
                resultHtml += `<td>${escapeHtml(word)}</td>`;
            } else {
                resultHtml += `<td>${escapeHtml(word)}</td>`;
            }
        }
        resultHtml += '</tr>';
    }
    resultHtml += "</table></form>";
    document.getElementById("resultArea").innerHTML = resultHtml;

    // 「予定の削除」ボタンをクリックしたときの処理
    document.getElementById("deleteEventBtn").addEventListener("click", async () =>{

        const nodeList = document.querySelectorAll('input[name="selectedEvent"]:checked');
        const selectedEvents = Array.from(nodeList).map(el => el.value);
        const apiGatewayBaseUrl = API_GATEWAY_URL;
        const postData = { event_ids: selectedEvents };

        if (!postData.event_ids || postData.event_ids.length === 0){
            window.alert("削除対象の予定が選択されていません");
            return;
        } else {
            if (window.confirm(`予定番号${selectedEvents}を削除してよろしいですか？`)){
                try {

                    // ログイン判定（実用上、idTokenの更新処理はしない）
                    idToken = localStorage.getItem("idToken");
                    if (!idToken){
                        window.alert("ログインしていません");
                        window.location.href = "index.html";
                        return;
                    }

                    const response = await fetch(`${apiGatewayBaseUrl}/delete-event`,{
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

                    const bodyJson = await response.json();
                    if (bodyJson.status === "success"){
                        // window.alert("選択された予定を削除しました");
                        location.reload(true);
                    } else {
                        console.log(bodyJson);
                        window.alert("予定の削除時にエラー発生");
                    }
                } catch (err) {
                    console.error(err);
                    window.alert("予定の削除時にエラー発生");
                }
            } else {
                document.querySelectorAll('input[name="selectedEvent"]:checked').forEach(el => el.checked=false);
            }
        }
    });
}

// 予定追加ボタン
document.getElementById("addEventBtn").addEventListener("click", () =>{
    window.location.href = `add-event.html?date=${encodeURIComponent(date)}`;
});

// パスワード変更ボタン
document.getElementById("changePasswordBtn").addEventListener("click", () => {
    window.location.href = "change-password.html";
});
