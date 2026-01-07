import logging
import json
import boto3
import pymysql
from datetime import date,datetime,timedelta
# カスタムモジュール読み込み
from mypackage.user_utils import get_userinfo
from mypackage.logging_utils import get_logger
from mypackage.ssm_utils import get_rdsinfo
from mypackage.secret_utils import get_secret

# ロガー設定
logger = get_logger()

# 指定されたevent_idの予定と予定詳細を取得
def get_event(event_id, user_id, secret_id, region_name, rds_host, rds_database):
    try:
        logger.debug("Calling get_secret")
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
                event_id = int(event_id)
                sql = """
                SELECT `event_id`,`date`,`event_name`,`event_detail` FROM event_t 
                WHERE `event_id` = %s and `user_id` = %s
                """
                cur.execute(sql, (event_id, user_id))
                row = cur.fetchone();
                if not row:
                    logger.error(f"Couldn't find event_id {event_id}")
                    return None
                # row_list = [row[0], datetime.strftime(row[1],"%Y-%m-%d"), row[2], row[3]]
                row_dict = {"event_id": row[0], "date": datetime.strftime(row[1],"%Y-%m-%d"), "event_name": row[2], "event_detail": row[3]}
                logger.debug(f"row_dict: {row_dict}")
                return row_dict

    except Exception as e:
        logger.error("Error occurrd in get_event")
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

        # GETパラメータから、event_idを取得する
        logger.debug("Getting paramater event_id")
        event_id = event.get("event_id")
        event_id = event.get("queryStringParameters",{}).get("event_id")
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
        
        logger.debug("Calling get_event")
        result = get_event(event_id, user_id, secret_id, region_name, rds_host, rds_database)
        result_dict = {
            "username": user_name,
            "data": result
        }
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

            }, ensure_ascii = False)
        }

    except Exception as e:
        logging.error(f"Error occurred: {e}")
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
            },ensure_ascii = False)
        }


if __name__ == "__main__":
    result = lambda_handler({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"queryStringParameters":{"event_id": 54}},None)
    print(result)
