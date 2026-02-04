import json
import boto3
import pymysql
from datetime import date,datetime,timedelta

from mypackage.user_utils import get_userinfo
from mypackage.logging_utils import get_logger
from mypackage.ssm_utils import get_rdsinfo
from mypackage.secret_utils import get_secret

# ロガー設定　
logger = get_logger()

# 指定日の予定と予定詳細を取得
def get_detail(date, user_id, secret_id, region_name, rds_host, rds_database):
    secret = get_secret(secret_id, region_name)
    try:
        with pymysql.connect(
            host = rds_host,
            user = secret["username"],
            password = secret["password"],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                date = datetime.strptime(date,"%Y-%m-%d").date()
                sql = """
                SELECT `event_id`,`date`,`event_name`,`event_detail` FROM event_t
                WHERE `date`= %s and `user_id` = %s
                ORDER BY `event_id`
                """
                cur.execute(sql,(date, user_id))
                rows = cur.fetchall()
                # result = [[row[0], datetime.strftime(row[1],"%Y-%m-%d"), row[2], row[3]] for row in rows ]
                rows_dict = [{"event_id": row[0], "date": datetime.strftime(row[1],"%Y-%m-%d"), "event_name": row[2], "event_detail": row[3]} for row in rows ]
                logger.debug(rows_dict)
                return rows_dict

    except Exception as e:
        logger.error(f"Error in get_detail: {e}")
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
                        "status" : "error",
                        "message" :"No user_id"
                    })
            }

        # GETパラメータを取得　空の場合はエラーを返す
        logger.debug(f"event: {event}")
        date = event.get("queryStringParameters",{}).get("date")
        # date = event.get("date",{})
        logger.debug(f"date: {date}")
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

        # その日の予定一覧を取得して返す
        result = get_detail(date, user_id, secret_id, region_name, rds_host, rds_database)
        result_dict = {"username": user_name , "data": result}
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
        logger.error(f"Error occurred: {e}" )
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
                "message": "Internal server error"
            }, ensure_ascii = False)
        }


if __name__ == "__main__":
    result = lambda_handler({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"queryStringParameters": {"date":"2025-12-28"}},None)
    print(result)

