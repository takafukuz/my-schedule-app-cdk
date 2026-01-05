import json
import boto3
from datetime import date,timedelta,datetime
import logging
import pymysql

from mypackage.user_utils import get_userinfo
from mypackage.logging_utils import get_logger
from mypackage.ssm_utils import get_rdsinfo
from mypackage.secret_utils import get_secret


# ロガー設定
logger = get_logger()


# event_tに新しい予定をinsert
def add_event(date,event_name, event_detail, user_id, user_name, secret_id, region_name, rds_host, rds_database):
    try:
        logger.debug("Connecting to databases ...")
        secret = get_secret(secret_id,region_name)
        with pymysql.connect(
            host = rds_host,
            user = secret["username"],
            password = secret["password"],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            logger.debug("Creating cursor ...")
            with conn.cursor() as cur:
                # sql = "select now();"
                date = datetime.strptime(date,"%Y-%m-%d").date()
                event_name = event_name.strip()
                event_detail = event_detail.strip()
                logger.debug(f"Arguments: {date}, {event_name}, {event_detail}, {user_id}, {user_name}")
                sql = """
                INSERT INTO event_t (`date`, `event_name`, `event_detail`, `user_id`, `user_name`)
                VALUES (%s,%s,%s,%s,%s)
                """
                cur.execute(sql,(date, event_name, event_detail, user_id, user_name))
                if cur.rowcount == 1:
                    conn.commit()
                    return True
                else:
                    conn.rollback()
                    return False

    except Exception as e:
       logger.error(f"Error in add_event: {e}")
       raise


def lambda_handler(event,context):
    try:
        # SSMパラメータストアからSecretsManager情報、RDS情報を取得
        logger.debug("Retrieving SSM parameters ...")
        secret_id = get_rdsinfo("/easydays/secret_id")
        region_name = get_rdsinfo("/easydays/region_name")
        rds_host  = get_rdsinfo("/easydays/rds_host")
        rds_database = get_rdsinfo("/easydays/rds_database")

        # ユーザー情報を取得 user_idが空の場合はエラーを返す
        logger.debug("Retrieving user information ...")
        userinfo = get_userinfo(event)
        user_id = userinfo["user_id"]
        user_name = userinfo["user_name"]
        if not userinfo["user_id"]:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                        "status" : "error",
                        "message" :"No user_id"
                    })
            }

        # 引数を取得
        # bodyの中身はjson文字列なのでjson.loadsでdictに変換する
        body = json.loads(event.get("body",{}))
        date = body.get("date","")
        event_name = body.get("event_name","")
        event_detail = body.get("event_detail","")

        if not date:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                        "status" : "error",
                        "message" :"No date found"
                    })
            }

        result = add_event(date, event_name, event_detail, user_id, user_name, secret_id, region_name, rds_host, rds_database)
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
                    "message": "OK"
                    }, ensure_ascii = False)
            }
    except Exception as e:
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


# ローカルテスト用
if __name__ == "__main__":
    logger.debug("Call lambda_handler")
    # bodyの中身は、JSON文字列で渡す
    result = lambda_handler({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"body": "{\"date\":\"2025-12-30\",\"event_name\":\"テスト予定名\",\"event_detail\":\"テスト予定詳細\"}"},None)
    print(result)
