'use strict';

document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    // ログイン関数を呼び出し
    let response;
    try {
        response = await login(username, password);
        
        if (!response) {
            document.getElementById("messageArea").innerHTML = "ログインできませんでした";
            return;
        }

        // 初回ログインの場合、初期パスワード変更画面に遷移
        if (response.ChallengeName === "NEW_PASSWORD_REQUIRED") {
            // console.log("1st time login");
            window.alert("初回ログインのため、パスワード変更が必要です");
            localStorage.setItem("username", username);
            localStorage.setItem("cognitoSession", response.Session);
            window.location.href = "change-initial-password.html";
            return;
        }
    } catch(error) {
        console.error("ログインエラー:", error);
        document.getElementById("messageArea").innerHTML = "ログイン処理中にエラーが発生しました";
        return;
    }

    // ログイン成功の場合、get-calendar.htmlに遷移
    if (response.AuthenticationResult) {
        // window.alert("ログイン成功");
        const idToken = response.AuthenticationResult.IdToken;
        const accessToken = response.AuthenticationResult.AccessToken;
        const refreshToken = response.AuthenticationResult.RefreshToken;
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

    try {
        const response = await fetch(authUrl,{
            method: "POST",
            headers: {
                "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
                "Content-Type": "application/x-amz-json-1.1"
            },
            body: JSON.stringify(postData)
        });

        if (!response.ok){
            throw new Error(`HTTP error: ${response.status}`);
        }

        return await response.json();

    } catch(error) {
        console.error("ログインAPIの呼び出しでエラー:", error);
        return null;
    }

}