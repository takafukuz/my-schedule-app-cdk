import boto3

ssm = boto3.client(service_name="ssm", region_name="ap-northeast-1")

def get_rdsinfo(name: str) -> str:
    res = ssm.get_parameter(
        Name=name,
        WithDecryption=False
    )
    return res['Parameter']['Value']

# デバッグ用
if __name__ == "__main__":
    result = get_rdsinfo("/easydays/rds_host")
    print(result)

# try exceptで括ったほうが良い？