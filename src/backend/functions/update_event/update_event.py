import json
import boto3
import logging
import pymysql
from datetime import date,datetime,timedelta

from mypackage.user_utils import get_userinfo
from mypackage.logging_utils import get_logger
from mypackage.secret_utils import get_secret
from mypackage.ssm_utils import get_rdsinfo


# ロガー設定
logger = get_logger()


# 予定情報をUPDATE
def update_event(event_id, date, event_name, event_detail, user_id, user_name, secret_id, region_name, rds_host, rds_database):
    try:
        logger.debug("Calling get_secret ...")
        secret = get_secret(secret_id,region_name)
        with pymysql.connect(
            host = rds_host,
            user = secret["username"],
            password = secret["password"],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                # 日付の文字列を日付型に変換
                date = datetime.strptime(date, "%Y-%m-%d").date()
                sql = """
                UPDATE event_t
                SET `date` = %s,
                `event_name` = %s,
                `event_detail` = %s,
                `user_name` = %s
                WHERE `event_id` = %s and `user_id` = %s;
                """
                cur.execute(sql,(date, event_name, event_detail, user_name, event_id, user_id))
                if cur.rowcount == 1:
                    logger.debug("Successfully updated")
                    conn.commit()
                    return True
                else:
                    logger.debug("Update failure")
                    conn.rollback()
                    return False
    
    except Exception as e:
        logger.error("Error occured in update_event")
        raise


def lambda_handler(event,context):
    try:
        # SSMパラメータストアからSecretsManager情報、RDS情報を取得
        logger.debug("Retrieving SSM parameters ...")
        secret_id = get_rdsinfo("/my_schedule_app/secret_id")
        region_name = get_rdsinfo("/my_schedule_app/region_name")
        rds_host  = get_rdsinfo("/my_schedule_app/rds_host")
        rds_database = get_rdsinfo("/my_schedule_app/rds_database")

        # ユーザー情報を取得 user_idが空の場合はエラーを返す
        userinfo = get_userinfo(event)
        user_id = userinfo["user_id"]
        user_name = userinfo["user_name"]
        if not user_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                    "status": "error",
                    "message": "No user_id"
                }, ensure_ascii = False)  
            }

        # 引数の取り出し
        # lambda上では、bodyの中身はjson文字列　json.loadsしてdictに変換する
        body = event.get("body", {})
        body = json.loads(body)
        event_id = body.get("event_id", "")
        date = body.get("date", "")
        event_name = body.get("event_name", "")
        event_detail = body.get("event_detail", "")
        # event_idがなければ、400エラーを返す
        if not event_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                    "status": "error",
                    "message": "No event_id"
                }, ensure_ascii = False)  
            }

        logger.debug("Calling update_event ...")
        result = update_event(event_id, date, event_name, event_detail, user_id, user_name, secret_id, region_name, rds_host, rds_database)
        result_dict = {
            "username": user_name,
            "data": result
        }
        if result:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                    "status": "success",
                    "message": result_dict
                },ensure_ascii = False)
            }
        else:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                    "status": "error",
                    "message": "No records updated"
                },ensure_ascii = False)
            }            

    except Exception as e:
        logger.debug(f"Error Occurred {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
            },
            "body": json.dumps({
                "status": "error",
                "message": repr(e)
            }, ensure_ascii = False)
        }


# ローカル確認用
if __name__ == "__main__":
    # lambdaでは、bodyの中身はJSON文字列となる
    result = lambda_handler({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"body":"{\"event_id\":113, \"date\": \"2025-12-20\", \"event_name\": \"サンプル予定\", \"event_detail\":\"サンプル予定詳細\"}"}, None)
    print(result)