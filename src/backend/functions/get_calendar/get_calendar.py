import json
import boto3
import pymysql
from datetime import date,timedelta,datetime
from collections import defaultdict
# カスタムモジュール読み込み
from mypackage.user_utils import get_userinfo
from mypackage.ssm_utils import get_rdsinfo
from mypackage.logging_utils import get_logger
from mypackage.secret_utils import get_secret


# ロガー設定
logger = get_logger()


# DBからデータ取得（日付、曜日、祝日、イベント）
def get_calendar(start_date, end_date, user_id, secret_id, region_name, rds_host, rds_database):
    try:
        logger.debug("Connecting to databases ...")
        secret = get_secret(secret_id, region_name)
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
                sql = """
                SELECT t1.`date`,t1.`weekday`,t3.`holiday_name`,t2.`event_name`
                FROM calendar_m t1
                LEFT OUTER JOIN ( select `date`, `event_name` from event_t where `user_id` = %s ) t2
                ON t1.`date`=t2.`date`
                LEFT OUTER JOIN holiday_m t3
                ON t1.`date`=t3.`date`
                where t1.`date` between %s and %s
                ORDER BY t1.`date`,t2.`event_name`
                """
                cur.execute(sql,(user_id, start_date, end_date))
                rows = cur.fetchall()
                # 同日にeventが複数ある場合の対応
                # "date","weekday","holiday_name"をKEYにして（これは一意となる前提）、
                # eventをリストで持つ辞書を要素とする、リストを作る
                # （補足）各レコードについて、（日付、曜日、祝日名）のセットをキーとし、予定を値とした、作業用辞書を作る
                # 値は、listなので、同じキーがあった場合は、値のリストにappendしていく
                # また、defaultdictなので、キーを予め作って置かなくても、エラーにならない
                # その後、キーを元の３つに分けて、要素名をつけたリストに作り直す（結果をjson形式で返すため）
                temp_dict = defaultdict(list)
                for date,weekday,holiday_name,event in rows:
                    temp_dict[(date.strftime("%Y-%m-%d"),weekday,holiday_name)].append(event)
                result_list = [
                    {"date": date, "weekday": weekday, "holiday_name": holiday_name,"events": event} 
                    for (date,weekday,holiday_name),event in temp_dict.items()
                ] 
                return result_list

    except Exception as e:
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
        logger.debug("Retrieving user information ...")
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

        # GETパラメータを取得
        logger.debug(f'event.queryStringParameters: {event["queryStringParameters"]}')
        dict_body = {"start_date": event["queryStringParameters"]["start_date"],"end_date": event["queryStringParameters"]["end_date"]}
        logger.debug(f"dict_body: {dict_body}")
        if not dict_body:
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
                    "message": "No body found"
                })
            }
        
        start_date = datetime.strptime(dict_body["start_date"],"%Y-%m-%d").date()
        end_date = datetime.strptime(dict_body["end_date"],"%Y-%m-%d").date()

        # DBからカレンダー情報を取得して、ユーザー名を付加して、json形式で返す
        result = get_calendar(start_date, end_date, user_id, secret_id, region_name, rds_host, rds_database)
        result_dict = {"username": user_name, "data": result}

        return {
            "statusCode": 200,
            "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
            },
            "body" : json.dumps({
                "status": "success",
                "message": result_dict
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return {
            "statusCode": 500,
            "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
            },
            "body" : json.dumps({
                "status": "error",
                "message": "Internal server error"
            }, ensure_ascii=False)
        }

# ローカルテスト用
if __name__ == "__main__":
    result = lambda_handler({"requestContext": {"authorizer": { "claims": {"sub":"77e4ba28-c0c1-70a1-b582-dba669f01e18","cognito:username":"dummyUserName"}}},"queryStringParameters": {"start_date": "2025-12-01","end_date":"2026-01-01"}},None)
    print(result)

