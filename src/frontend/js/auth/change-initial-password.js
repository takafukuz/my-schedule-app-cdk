
'use strict';

// submitで括る
document.getElementById("passwordForm").addEventListener("submit", async function(e){
    e.preventDefault();

    const username = localStorage.getItem("username");
    const newPassword = document.getElementById("newPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (newPassword !== confirmPassword){
        document.getElementById("messageArea").innerHTML = "新しいパスワードが一致しません";
        document.getElementById("passwordForm").reset();
        return;
    }

    // パスワード変更の関数を呼ぶ
    const result = await changeInitialPassword(username, newPassword);

    console.log(result);
    // パスワード変更＝ログイン成功
    if (result.AuthenticationResult) {
        console.log("Login OK");
        const idToken = result.AuthenticationResult.IdToken;
        const accessToken = result.AuthenticationResult.AccessToken;
        const refreshToken = result.AuthenticationResult.RefreshToken;

        localStorage.setItem("idToken", idToken);
        localStorage.setItem("accessToken", accessToken);
        localStorage.setItem("refreshToken", refreshToken);

        document.getElementById("messageArea").innerHTML = "パスワードを変更しました";
        document.getElementById("messageArea").style.color = "#2e7d32";
        // console.log(idToken)

        setTimeout(() => {
            window.location.href = "get-calendar.html";
        }, 1500);
        return;

    } else {
        console.log("Login NG");
        console.log(result);
        document.getElementById("messageArea").innerHTML = "パスワード変更に失敗しました";
        setTimeout(() => {
            window.location.href = "index.html";
        }, 2000);
        return;
    }

})

// パスワード変更の関数を定義する
async function changeInitialPassword(username, newPassword) {

    const clientId = CognitoConfig.UserPoolClientId;
    const session = localStorage.getItem("cognitoSession");
    const region_name = CognitoConfig.Region;
    const apiUrl = `https://cognito-idp.${region_name}.amazonaws.com/`;

    const postData = {
        ChallengeName : "NEW_PASSWORD_REQUIRED",
        ClientId : clientId,
        Session : session,
        ChallengeResponses : {
            USERNAME : username,
            NEW_PASSWORD : newPassword
        }
    }
    
    try {
        const res = await fetch(apiUrl, {
            method : "POST",
            headers : {
            "x-Amz-Target" : "AWSCognitoIdentityProviderService.RespondToAuthChallenge",
            "Content-Type" : "application/x-amz-json-1.1"
            },
            body : JSON.stringify(postData)
        })

        return await res.json();
    } catch (error) {
        console.log(error)
    }
}
