async function refreshCognitoToken(){
    // const regionName = "ap-northeast-1";
    // const clientId = "1l3mhekbasc1sqopjk3gn67eks";
    // const clientId = "106pvb1kqca1e3vlghklsf4j51";
    const regionName = CognitoConfig.Region;
    const clientId = CognitoConfig.UserPoolClientId;

    const authUrl = `https://cognito-idp.${regionName}.amazonaws.com/`;
    const refreshToken = localStorage.getItem("refreshToken")

    if (!refreshToken) {
        return { error: "NoRefreshToken", message: "refreshToken がありません" };
    }

    const postData = {
        AuthFlow: "REFRESH_TOKEN_AUTH",
        ClientId: clientId,
        AuthParameters: {
            REFRESH_TOKEN : refreshToken
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