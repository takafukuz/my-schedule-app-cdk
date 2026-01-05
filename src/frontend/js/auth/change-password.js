
'use strict';

document.addEventListener("DOMContentLoaded", async function(){
    // idTokenの更新処理
    const refreshRes = await refreshCognitoToken();
    console.log(refreshRes);
    if (refreshRes.AuthenticationResult){
    console.log("Refreshed Token successfully")
    localStorage.setItem("idToken", refreshRes.AuthenticationResult.IdToken);
    localStorage.setItem("accessToken", refreshRes.AuthenticationResult.AccessToken);

    idToken = refreshRes.AuthenticationResult.IdToken;

    } else {
        document.getElementById("messageArea").innerHTML = "トークンの更新に失敗しました";
        setTimeout(() => {
            window.location.href = "index.html";
        }, 2000);
        return;
    }
})

document.getElementById("myForm").addEventListener("submit", async function(e){
    e.preventDefault();

    const currentPassword = document.getElementById("currentPassword").value;
    const newPassword = document.getElementById("newPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (newPassword !== confirmPassword) {
        document.getElementById("messageArea").innerHTML = "新しいパスワードが一致しません";
        document.getElementById("newPassword").value = "";
        document.getElementById("confirmPassword").value = "";
        return;
    }

    const result = await changePassword(currentPassword, newPassword);

    console.log(result);

    if (result.ok){
        document.getElementById("messageArea").innerHTML = "パスワード変更が成功しました";
        document.getElementById("messageArea").style.color = "#2e7d32";
        setTimeout(() => {
            window.location.href = "get-calendar.html";
        }, 1500);
        return;
    } else {
        document.getElementById("messageArea").innerHTML = "パスワード変更に失敗しました";
        document.getElementById("myForm").reset();
    }
})

async function changePassword(currentPassword, newPassword) {
    const region = CognitoConfig.Region;
    const url = `https://cognito-idp.${region}.amazonaws.com/`;

    const accessToken = localStorage.getItem("accessToken");

    const postData = {
        PreviousPassword: currentPassword,
        ProposedPassword: newPassword,
        AccessToken: accessToken
    };

    const res = await fetch(url, {
        method: "POST",
        headers: {
            "X-Amz-Target": "AWSCognitoIdentityProviderService.ChangePassword",
            "Content-Type": "application/x-amz-json-1.1"
        },
        body: JSON.stringify(postData)
    });

    // 成功してもbodyは空で返ってくるので、HTTPステータスで判定する
    // 成功（HTTP 200番台の場合）
    if (res.ok) {
        return { ok: true };
    }

    // それ以外の場合＝失敗（HTTP 400 など）は、
    // responsにエラー内容が含まれているので、戻り値に含める
    const errorJson = await res.json();
    return {
        ok: false,
        error: errorJson.__type || "no info",
        message: errorJson.message || "no info"
    };
}