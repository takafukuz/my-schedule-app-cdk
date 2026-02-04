import logging
from datetime import date,timedelta,datetime
import pymysql
import boto3
import json
import calendar
import csv

# カスタムモジュール読み込み
from mypackage.user_utils import get_userinfo
from mypackage.ssm_utils import get_rdsinfo
from mypackage.logging_utils import get_logger
from mypackage.secret_utils import get_secret

# ロガー設定
logger = get_logger()

# 初期テーブルの作成
def create_table(secret_id, region_name, rds_host, rds_database):
    try:
        logger.debug("Calling get_secret ...")
        secret = get_secret(secret_id, region_name)
        logger.debug("Connecting Database")
        with pymysql.connect(
            host = rds_host,
            user = secret['username'],
            password = secret['password'],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                logger.info("Creating calendar_m ...")
                sql = """
                CREATE TABLE IF NOT EXISTS `calendar_m` (
                    `date` DATE NOT NULL,
                    `weekday` VARCHAR(50) NOT NULL DEFAULT '' COLLATE 'utf8mb4_0900_ai_ci',
                    PRIMARY KEY (`date`) USING BTREE
                )
                COLLATE='utf8mb4_0900_ai_ci'
                ENGINE=InnoDB
                """
                cur.execute(sql)
                logger.info("Creating holiday_m ...")
                sql = """
                CREATE TABLE IF NOT EXISTS `holiday_m` (
                    `date` DATE NOT NULL,
                    `holiday_name` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_0900_ai_ci',
                    PRIMARY KEY (`date`) USING BTREE
                )
                COLLATE='utf8mb4_0900_ai_ci'
                ENGINE=InnoDB
                """
                cur.execute(sql)
                logger.info("Creating event_t ...")
                sql = """
                CREATE TABLE IF NOT EXISTS `event_t` (
                    `event_id` INT NOT NULL AUTO_INCREMENT,
                    `date` DATE NOT NULL,
                    `event_name` VARCHAR(200) NOT NULL COLLATE 'utf8mb4_0900_ai_ci',
                    `event_detail` TEXT NULL DEFAULT NULL COLLATE 'utf8mb4_0900_ai_ci',
                    `user_id` VARCHAR(200) NULL DEFAULT NULL COLLATE 'utf8mb4_0900_ai_ci',
                    `user_name` VARCHAR(200) NULL DEFAULT NULL COLLATE 'utf8mb4_0900_ai_ci',
                    PRIMARY KEY (`event_id`) USING BTREE,
                    INDEX `FK_event_t_calendar_m` (`date`) USING BTREE,
                    CONSTRAINT `FK_event_t_calendar_m` FOREIGN KEY (`date`) REFERENCES `calendar_m` (`date`) ON UPDATE NO ACTION ON DELETE NO ACTION
                )
                COLLATE='utf8mb4_0900_ai_ci'
                ENGINE=InnoDB
                AUTO_INCREMENT=128
                """
                cur.execute(sql)
                conn.commit()
                logger.info("Creating 3 tables completed.")
                return True
    except Exception as e:
        logger.error(f"Error occurred in create_table: {e}")
        raise

# 日付と曜日の情報を生成する
# ジェネレート関数として、ループ中に値を返す
def generate_dateinfo(start_date, end_date):
    weekday_name = ["月","火","水","木","金","土","日"]
    wk_date = start_date

    while wk_date <= end_date:
        wk_weekday_num = calendar.weekday(wk_date.year,wk_date.month,wk_date.day)
        wk_weekday_name = weekday_name[wk_weekday_num]
        wk_date_str = wk_date.strftime("%Y-%m-%d")
        yield(wk_date_str,wk_weekday_name)
        wk_date += timedelta(days=1)

# 生成した日付情報をもとに、calendar_mにINSERT/UPDATEする
def insert_dateinfo(start_date, end_date, secret_id, region_name, rds_host, rds_database):
    try:
        secret = get_secret(secret_id, region_name)
        with pymysql.connect(
            host = rds_host,
            user = secret['username'],
            password = secret['password'],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                logging.info("Create wk_calendar ...")
                sql = """
                CREATE TABLE IF NOT EXISTS `wk_calendar` (
                    `date` DATE NOT NULL,
                    `weekday` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_0900_ai_ci',
                    PRIMARY KEY (`date`) USING BTREE
                )
                COLLATE='utf8mb4_0900_ai_ci'
                ENGINE=InnoDB;
                """
                cur.execute(sql)
                logging.info("Truncating wk_calendar ...")
                cur.execute('truncate table wk_calendar')
                # workテーブルに生成した日付と曜日をinsertする
                for row in generate_dateinfo(start_date,end_date):
                    sql="insert into wk_calendar (`date`,`weekday`) values (%s,%s)"
                    logging.info("Inserting values {},{} ".format(row[0],row[1]))
                    cur.execute(sql,row)
                # calendar_mに存在する日付情報をupdate
                logging.info("Updating existing data")
                sql = """
                update calendar_m as t1
                inner join wk_calendar as t2
                on t1.`date` = t2.`date`
                set t1.`weekday` = t2.`weekday`
                where t1.`weekday` <> t2.`weekday`
                """
                cur.execute(sql)
                # calendar_mに存在しない日付情報をinsert
                logging.info("Inserting data into calendar_m")
                sql = """
                insert into calendar_m (`date`,`weekday`)
                select t1.`date`,t1.`weekday` from wk_calendar as t1
                left outer join calendar_m as t2
                on t1.`date` = t2.`date`
                where t2.`date` is null
                """
                cur.execute(sql)
                conn.commit()
                logging.info("Commit completed")
                return True
            
    except Exception as e:
        logger.error(f"Error occurred in insert_dateinfo: {e}")
        raise

# 祝日情報更新用ストアドを作成する
def create_sp(secret_id, region_name, rds_host, rds_database):
    try:
        secret = get_secret(secret_id, region_name)
        with pymysql.connect(
            host = rds_host,
            user = secret['username'],
            password = secret['password'],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                logging.info("Dropping sp if exists ...")
                cur.execute("DROP PROCEDURE IF EXISTS `update_holiday_m`")
                logging.info("Creating sp_update_holiday_calendar ...")
                sql = """
                CREATE PROCEDURE update_holiday_m()
                BEGIN
                    -- テンポラリテーブルを作成
                    DROP TEMPORARY TABLE IF EXISTS tmp_holiday;
                    CREATE TEMPORARY TABLE tmp_holiday (
                        `date` DATE,
                        `name` VARCHAR(50)
                    );
                    -- 取込テーブルから重複を削除
                    INSERT INTO tmp_holiday (`date`,`name`)
                    SELECT DISTINCT `date`, holiday_name
                    FROM wk_holiday_calendar;
                    -- 取込テーブルをもとにholiday_mをupdate
                    UPDATE holiday_m t1
                    JOIN tmp_holiday t2
                    ON t1.`date` = t2.`date`
                    SET t1.holiday_name = t2.`name`
                    WHERE t1.holiday_name <> t2.`name`;
                    -- 取込テーブルにあって、holiday_mにないものをinsert
                    INSERT INTO holiday_m (`date`,`holiday_name`)
                    SELECT t2.`date`, t2.`name`
                    FROM tmp_holiday t2
                    LEFT JOIN holiday_m t1
                    ON t1.`date` = t2.`date`
                    WHERE t1.`date` IS NULL;
                END
                """
                cur.execute(sql)
                conn.commit()
                logging.info("Creating sp_update_holiday_calendar completed")
                return True
    except Exception as e:
        logger.error(f"Error occurred in create_sp: {e}")
        raise

# S3バケットから祝日情報CSVを取得
def download_csv(bucket_name, object_key, local_path):
    client = boto3.client(service_name = 's3')
    client.download_file(bucket_name, object_key, local_path)

# 祝日情報をCSVからwkテーブルに取り込む
def import_holiday_data(secret_id, region_name, rds_host, rds_database, local_path):
    try:
        secret = get_secret(secret_id, region_name)
        conn = pymysql.connect(
            host = rds_host,
            user = secret['username'],
            password = secret['password'],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        )
        # 作業テーブルを作成・クリア後、CSVファイルの2行目から作業テーブルにinsertする
        cur = conn.cursor()
        sql = """
        CREATE TABLE IF NOT EXISTS `wk_holiday_calendar` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `date` DATE NOT NULL DEFAULT '1900-01-01',
            `holiday_name` VARCHAR(50) NOT NULL DEFAULT '0' COLLATE 'utf8mb4_0900_ai_ci',
            PRIMARY KEY (`id`) USING BTREE
        )
        COLLATE='utf8mb4_0900_ai_ci'
        ENGINE=InnoDB
        AUTO_INCREMENT=1051;
        """
        cur.execute(sql)
        cur.execute("truncate table `wk_holiday_calendar`")

        with open(local_path,newline='',encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                # print(row[0],row[1])
                sql=f"insert into `wk_holiday_calendar`(date,holiday_name) values(%s, %s);"
                cur.execute(sql,row)

        conn.commit()
    except Exception as e:
        logger.error(f"Error occurred in import_holiday_data: {e}")
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# wkテーブルをもとにholiday_mを更新する
def kick_sp(secret_id, region_name, rds_host, rds_database):
    try:
        secret = get_secret(secret_id, region_name)
        with pymysql.connect(
            host = rds_host,
            user = secret['username'],
            password = secret['password'],
            database = rds_database,
            charset = "utf8mb4",
            connect_timeout = 5
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("CALL `update_holiday_m`()")
                conn.commit()
                return {"status":"success"}

    except Exception as e:
        logger.error(f"Error occurred in kick_sp: {e}")
        raise

def lambda_handler(event,context):
    try:
        # SSMパラメータストアからSecretsManager情報、RDS情報を取得
        logger.debug("Retrieving SSM parameters ...")
        secret_id = get_rdsinfo("/my_schedule_app/secret_id")
        region_name = get_rdsinfo("/my_schedule_app/region_name")
        rds_host  = get_rdsinfo("/my_schedule_app/rds_host")
        rds_database = get_rdsinfo("/my_schedule_app/rds_database")
        bucket_name = get_rdsinfo("/my_schedule_app/data_bucket")

        start_date = date.today()
        end_date = start_date + timedelta(days=365)
        # end_date = date(2026,12,31) # 終了日を指定したい場合

        # 祝日情報CSV情報
        object_key = "holiday-data.csv"
        local_path = f"/tmp/{object_key}"

        # 初期テーブル作成実行
        logger.debug("Calling create_table ...")
        result = create_table(secret_id, region_name, rds_host, rds_database)

        # 日付情報のcalendar_mへのINSERT/UPDATE
        logger.debug("Calling insert_dateinfo ...")
        result = insert_dateinfo(start_date, end_date, secret_id, region_name, rds_host, rds_database)

        # 祝日情報更新用ストアド作成
        logger.debug("Calling create_sp ...")
        result = create_sp(secret_id, region_name, rds_host, rds_database)

        # 祝日情報の取込と更新用ストアドの実施
        logger.debug("Calling download_csv ...")
        result = download_csv(bucket_name, object_key, local_path)
        logger.debug("Calling import_holiday_data ...")
        rerult = import_holiday_data(secret_id, region_name, rds_host, rds_database, local_path)
        logger.debug("Calling kick_sp ...")
        result = kick_sp(secret_id, region_name, rds_host, rds_database)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status":"success",
                "message": None
                })
        }

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "error",
                "message": "Internal server error"
            })
        }

