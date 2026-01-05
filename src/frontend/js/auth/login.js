'use strict';

document.getElementById("loginForm").addEventListener("submit", async function(e){
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    // ログイン関数を呼び出し
    const res = await login(username,password);
    console.log(res);

    // 初回ログインの場合、初期パスワード変更画面に遷移
    if (res.ChallengeName === "NEW_PASSWORD_REQUIRED") {
        console.log("1st time login");
        window.alert("初回ログインのため、パスワード変更が必要です");
        localStorage.setItem("username", username);
        localStorage.setItem("cognitoSession", res.Session);
        window.location.href = "change-initial-password.html";
        return;
    }

    // ログイン成功の場合、get-calendar.htmlに遷移
    if (res.AuthenticationResult){
    // window.alert("ログイン成功");
    const idToken = res.AuthenticationResult.IdToken;
    const accessToken = res.AuthenticationResult.AccessToken;
    const refreshToken = res.AuthenticationResult.RefreshToken;

    localStorage.setItem("idToken", idToken);
    localStorage.setItem("accessToken", accessToken);
    localStorage.setItem("refreshToken", refreshToken);

    window.location.href = "get-calendar.html";
    } else {
    document.getElementById("messageArea").innerHTML = "ログインできませんでした";
    }
});

async function login(username,password){
    const regionName = CognitoConfig.Region;
    const clientId = CognitoConfig.UserPoolClientId;

    const authUrl = `https://cognito-idp.${regionName}.amazonaws.com/`;

    const postData = {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: clientId,
    AuthParameters: {
        USERNAME: username,
        PASSWORD: password
    }
    };

    const res = await fetch(authUrl,{
    method: "POST",
    headers: {
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        "Content-Type": "application/x-amz-json-1.1"
    },
    body: JSON.stringify(postData)
    });

    return await res.json();
}