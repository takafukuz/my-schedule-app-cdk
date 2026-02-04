async function refreshCognitoToken(){

    const regionName = CognitoConfig.Region;
    const clientId = CognitoConfig.UserPoolClientId;

    const authUrl = `https://cognito-idp.${regionName}.amazonaws.com/`;
    const refreshToken = localStorage.getItem("refreshToken");

    if (!refreshToken) {
        return {
            status: "error",
            message: "No Refresh Token"
        };
    }

    const postData = {
        AuthFlow: "REFRESH_TOKEN_AUTH",
        ClientId: clientId,
        AuthParameters: {
            REFRESH_TOKEN: refreshToken
        }
    };

    let response;
    try {
        response = await fetch(authUrl,{
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
    } catch (error) {
        console.error("トークン更新APIの呼び出しでエラー:", error);
        return {
            status: "error",
            message: "Api Error"
        };
    }
}