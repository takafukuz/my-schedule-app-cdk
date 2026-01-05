def get_userinfo(event):
    """Cognitoから入ってくるユーザー情報をeventから取り出す"""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub", "")
    user_name = claims.get("cognito:username", "")
    return {"user_id": user_id, "user_name": user_name}


if __name__ == "__main__":
    result = get_userinfo({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"body": "{\"event_ids\":[78]}"})
    print(result)