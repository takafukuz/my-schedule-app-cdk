import json
import boto3


# SecretsManagerからDB認証情報を取得
def get_secret(secret_id,region_name):
    client = boto3.client(
        service_name = "secretsmanager",
        region_name = region_name
    )

    res = client.get_secret_value(SecretId = secret_id)
    return json.loads(res["SecretString"])

# try exceptで括ったほうが良い？