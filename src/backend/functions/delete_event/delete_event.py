import json
import logging
import boto3
import pymysql
from datetime import date, datetime

from mypackage.user_utils import get_userinfo
from mypackage.logging_utils import get_logger
from mypackage.secret_utils import get_secret
from mypackage.ssm_utils import get_rdsinfo


# ロガー設定
logger = get_logger()


# 選択された予定を削除する
def delete_event(event_ids, user_id, secret_id, region_name, rds_host, rds_database):
    # event_idはリスト
    try: 
        secret = get_secret(secret_id, region_name)
        with pymysql.connect(
            host = rds_host,
            user = secret["username"],
            password = secret["password"],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                logger.debug(f"event_ids: {event_ids}")
                num_of_events = len(event_ids)
                placeholders = ", ".join(["%s"] * num_of_events)
                sql = f"delete from event_t where `event_id` in ( {placeholders} ) and `user_id` = %s;"
                logger.debug(f"sql: {sql}")
                # event_ids（リスト）とuser_idを並べるため、event_idsをアンパック（＊）する必要がある
                cur.execute(sql,(*event_ids, user_id))
                if cur.rowcount == num_of_events:
                    conn.commit()
                    return True
                else:
                    conn.rollback()
                    return False

    except Exception as e:
        logger.error(f"Error occurred in delete_event: {e}")
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

        # 引数の取得
        body = event.get("body", {})
        event_ids = json.loads(body).get("event_ids", [])
        logger.debug(f"event_ids: {event_ids}, {type(event_ids)}")
        if not event_ids:
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
                    "message": "No event_ids"
                }, ensure_ascii = False)  
            }

        # 削除の実施
        result = delete_event(event_ids, user_id, secret_id, region_name, rds_host, rds_database)
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
                    "message": "No records deleted"
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


# ローカル動作確認用
if __name__ == "__main__":
    result = lambda_handler({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"body": "{\"event_ids\":[124]}"}, None)
    print(result)

