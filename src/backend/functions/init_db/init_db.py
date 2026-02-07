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

class InitDbBatch:
    def __init__(self, host, user, password, database, start_date, end_date, bucket_name, object_key, download_dir):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.start_date = start_date
        self.end_date = end_date
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.local_path = f"{download_dir}/{object_key}"
        # Connectionオブジェクトの初期化
        self.conn = None

    def connect_db(self):
        self.conn = pymysql.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            database = self.database,
            charset = "utf8mb4",
            connect_timeout = 5
        )
    
    def create_tables(self):
        with self.conn.cursor() as cur:
            # 単純なテーブル作成はSP化しないほうが良いらしい
            # calendar_mテーブルの作成
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
            # holiday_mテーブルの作成
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
            # event_tテーブルの作成
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
            AUTO_INCREMENT=1
            """
            cur.execute(sql)

    # generate_dateinfoで日付と曜日の情報を生成しながら、calendar_mにinsertする
    def insert_dateinfo(self, start_date, end_date):
        with self.conn.cursor() as cur:
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
            cur.execute('truncate table wk_calendar')
            # workテーブルに生成した日付と曜日をinsertする
            for row in self.generate_dateinfo(start_date, end_date):
                sql="insert into wk_calendar (`date`, `weekday`) values (%s, %s)"
                # logger.info("Inserting values {},{} ".format(row[0],row[1]))
                # rowは、(日付,曜日)のタプル
                cur.execute(sql, row)
            # calendar_mに存在する日付情報をupdate
            sql = """
            update calendar_m as t1
            inner join wk_calendar as t2
            on t1.`date` = t2.`date`
            set t1.`weekday` = t2.`weekday`
            where t1.`weekday` <> t2.`weekday`
            """
            cur.execute(sql)
            # calendar_mに存在しない日付情報をinsert
            sql = """
            insert into calendar_m (`date`,`weekday`)
            select t1.`date`,t1.`weekday` from wk_calendar as t1
            left outer join calendar_m as t2
            on t1.`date` = t2.`date`
            where t2.`date` is null
            """
            cur.execute(sql)

    # 日付と曜日の情報を生成する
    # ジェネレート関数として、ループ中に値を返す
    def generate_dateinfo(self, start_date, end_date):
        weekday_name = ["月","火","水","木","金","土","日"]
        wk_date = start_date

        while wk_date <= end_date:
            wk_weekday_num = calendar.weekday(wk_date.year,wk_date.month,wk_date.day)
            wk_weekday_name = weekday_name[wk_weekday_num]
            wk_date_str = wk_date.strftime("%Y-%m-%d")
            yield(wk_date_str,wk_weekday_name)
            wk_date += timedelta(days=1)

    # 祝日情報CSVファイルをS3バケットからダウンロードする
    def download_csv(self, bucket_name, object_key, local_path):
        logger.info(f"バケット {bucket_name} から {object_key} を {local_path} にダウンロードします")
        client = boto3.client("s3")
        client.download_file(bucket_name, object_key, local_path)
        logger.info("CSVファイルのダウンロードに成功しました")

    # 祝日情報CSVファイルのデータを取込テーブルに入れる
    # bulkインサートが良いのだろうけど、CSVファイルの行ごとにループを回す練習
    def import_holiday_data(self, local_path):
        with self.conn.cursor() as cur:
            sql = """
            CREATE TABLE IF NOT EXISTS `wk_holiday_calendar` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `date` DATE NOT NULL DEFAULT '1900-01-01',
                `holiday_name` VARCHAR(50) NOT NULL DEFAULT '0' COLLATE 'utf8mb4_0900_ai_ci',
                PRIMARY KEY (`id`) USING BTREE
            )
            COLLATE='utf8mb4_0900_ai_ci'
            ENGINE=InnoDB
            AUTO_INCREMENT=1;
            """
            cur.execute(sql)
            sql = "truncate table `wk_holiday_calendar`"
            cur.execute(sql)
            with open(local_path, newline="", encoding="utf-8") as f:
                data = csv.reader(f)
                next(data)
                for row in data:
                    sql = "INSERT INTO `wk_holiday_calendar` (`date`, `holiday_name`) VALUES (%s, %s);"
                    cur.execute(sql, (row[0], row[1]))
    
    def update_holiday_m(self):
        with self.conn.cursor() as cur:
            # ストアドプロシージャ作成
            sql = "DROP PROCEDURE IF EXISTS `update_holiday_m`;"
            cur.execute(sql)
            # （要検討）祝日の日付が変更になった場合への対応
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
            # ストアドプロシージャの実行
            sql = "CALL `update_holiday_m`();"
            cur.execute(sql)

    # 全体実行用
    def run(self):
        # 各メソッドの引数は、インスタンス変数から渡す
        try:
            logger.info("DBに接続")
            self.connect_db()

            logger.info("初期テーブルの作成")
            self.create_tables()

            logger.info("カレンダーMへの日付データ投入")
            self.insert_dateinfo(self.start_date, self.end_date)

            logger.info("祝日情報CSVのダウンロード")
            self.download_csv(self.bucket_name, self.object_key, self.local_path)

            logger.info("祝日情報データのインポート")
            self.import_holiday_data(self.local_path)

            logger.info("祝日Mの更新")
            self.update_holiday_m()

            # 最後にまとめてcommitして終了
            logger.info("コミット実行")
            self.conn.commit()

            logger.info("全処理終了")

            return {
                "status": "success",
                "message": "DB初期化処理が正常に完了しました"
            }
        
        except Exception as e:
            logger.error(f"エラー発生: {repr(e)}")

            if self.conn:
                self.conn.rollback()
                logger.error("ロールバックを実行しました")

            return {
                "status": "error",
                "message": repr(e)
            }
        
        finally:
            if self.conn:
                self.conn.close()
                logger.info("DB接続をclose")


def lambda_handler(event,context):
    # SSMパラメータストアから情報取得
    secret_id = get_rdsinfo("/my_schedule_app/secret_id") 
    region_name = get_rdsinfo("/my_schedule_app/region_name")
    rds_host  = get_rdsinfo("/my_schedule_app/rds_host")
    rds_database = get_rdsinfo("/my_schedule_app/rds_database")
    bucket_name = get_rdsinfo("/my_schedule_app/data_bucket")

    # SecretsManagerから情報取得
    secret = get_secret(secret_id, region_name)

    # DB接続情報(辞書で入れておいて、アンパックで渡す)
    config = {
        "host": rds_host,
        "user": secret["username"],
        "password": secret["password"],
        "database": rds_database,
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=365),
        "bucket_name": bucket_name,
        "object_key": "holiday-data.csv",
        # "download_dir": "tests/sandbox", # ローカル動作確認用
        "download_dir": "/tmp", # 本番用
    }

    # 処理実行
    batch = InitDbBatch(**config)
    result = batch.run()

    return result

# ローカル動作確認用
if __name__ == "__main__":
    result = lambda_handler(None, None)
    print(f"処理結果: {result}")