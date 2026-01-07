from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    aws_s3_deployment as s3_deployment,
    aws_lambda,
    Duration,
    aws_ec2 as ec2,
    aws_apigateway as apigw,
    aws_secretsmanager as secretsmanager,
    aws_kms as kms,
    aws_cognito as cognito,
    CfnOutput,
    aws_iam as iam,
    aws_rds as rds,
    aws_ssm as ssm,
    CustomResource,
    custom_resources as cr,
)
from constructs import Construct

class MyScheduleAppCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 公開用バケット（バケット名は固定しない）
        website_bucket = s3.Bucket(
            self,
            "WebsiteBucket",
            # bucket_name = "my-schedule-app-prod-site-bucket",
            website_index_document = "index.html",
            public_read_access = True,
            block_public_access = s3.BlockPublicAccess(
                block_public_acls = False,
                block_public_policy = False,
                ignore_public_acls = False,
                restrict_public_buckets = False,
            ),
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
        )

        # URLを出力
        CfnOutput(
            self,
            "WebsiteBucketURLOutput",
            value = website_bucket.bucket_website_url,
        )

        # データ用バケット（バケット名は動的とする）
        data_bucket = s3.Bucket(
            self,
            "DataBucket",
            public_read_access = False,
            block_public_access = s3.BlockPublicAccess.BLOCK_ALL,
            encryption = s3.BucketEncryption.S3_MANAGED,
            versioned = True,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
        )
        
        # CSVファイルアップロード
        csv_upload = s3_deployment.BucketDeployment(
            self,
            "CsvUpload",
            sources = [
                s3_deployment.Source.asset("./data"),
            ],
            destination_bucket= data_bucket,
        )

        # vpc作成(サブネットは、パブリック2個、プライベート2個)
        my_vpc = ec2.Vpc(
            self,
            "MyVpc",
            ip_addresses = ec2.IpAddresses.cidr("10.1.0.0/16"),
            max_azs = 2,
            subnet_configuration = [
                ec2.SubnetConfiguration(
                    name = "my-private-subnet",
                    subnet_type = ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask = 24,
                ),
                ec2.SubnetConfiguration(
                    name = "my-public-subnet",
                    subnet_type = ec2.SubnetType.PUBLIC,
                    cidr_mask = 24,
                ),
            ],
        )

        # rds用サブネットグループの作成
        my_subnet_group = rds.SubnetGroup(
            self,
            "MySubnetGroup",
            description = "Subnet Group for RDS",
            vpc = my_vpc,
            vpc_subnets = ec2.SubnetSelection(
                subnets = my_vpc.isolated_subnets
            )
        )

        # lambda用サブネットの指定
        my_subnet_for_lambda = ec2.SubnetSelection(
            subnets = [ my_vpc.isolated_subnets[0] ]
        )

        # lambda用SG
        my_sg_for_lambda = ec2.SecurityGroup(
            self,
            "MySecurityGroupForLambda",
            vpc = my_vpc,
            description = "Security Group for Lambda",
            allow_all_outbound = True,
        )
        
        # 踏み台サーバ用SG
        my_sg_for_ec2 = ec2.SecurityGroup(
            self,
            "MySecurityGroupForEC2",
            vpc = my_vpc,
            description = "Security Group for EC2",
            allow_all_outbound = True,
        )

        my_sg_for_ec2.add_ingress_rule(
            peer = ec2.Peer.any_ipv4(),
            connection = ec2.Port.tcp(22),
            description = "Allow SSH from anywhere",
        )

        # エンドポイント(SSM,SecretsManager)のために同じSG内の通信を全て許可
        # エンドポイント用のSG作って、lambda用のSGから、443のインバウンドを許可したほうが良いかも
        my_sg_for_lambda.add_ingress_rule(
            peer = my_sg_for_lambda,
            connection = ec2.Port.all_traffic(),
        )

        # RDS用SG（アウトバウンドは開けなくて良い）
        my_sg_for_rds = ec2.SecurityGroup(
            self,
            "MySecurityGroupForRDS",
            vpc = my_vpc,
            description = "Security Group for RDS",
        )

        # RDS用SGで、lambda用SGからの通信を許可
        my_sg_for_rds.add_ingress_rule(
            peer = my_sg_for_lambda,
            connection = ec2.Port.tcp(3306),
        )

        # RDS用SGで、踏み台サーバ用SGからの通信を許可
        my_sg_for_rds.add_ingress_rule(
            peer = my_sg_for_ec2,
            connection = ec2.Port.tcp(3306),
        )

        # SSM向けエンドポイント作成
        my_vpc.add_interface_endpoint(
            "SsmEndpoint",
            service = ec2.InterfaceVpcEndpointAwsService.SSM,
            subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
        )

        # Secrets Manager向けエンドポイント作成
        my_vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service = ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
        )

        # S3向けエンドポイント（ゲートウェイ型）作成
        my_vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service = ec2.GatewayVpcEndpointAwsService.S3,
            subnets = [my_subnet_for_lambda],
        )

        # 踏み台サーバ作成
        my_ami = ec2.MachineImage.latest_amazon_linux2023()

        # 鍵ファイルの作成（秘密鍵はパラメータストアに出力される）
        my_keypair = ec2.KeyPair(
            self,
            "MyKeyPair",
        )

        # キーペア名を出力
        CfnOutput(
            self,
            "MyKeyPairNameOutput",
            value = my_keypair.key_pair_name,
            description = "Key Pair for Bastion Host"
        )

        my_instance = ec2.Instance(
            self,
            "MyInstance",
            instance_type = ec2.InstanceType("t3.nano"),
            machine_image = my_ami,
            vpc = my_vpc,
            vpc_subnets = ec2.SubnetSelection(
                subnets = [ my_vpc.public_subnets[0]]
            ),
            security_group = my_sg_for_ec2,
            key_pair = my_keypair,
        )

        # 踏み台サーバのIPアドレスの出力
        CfnOutput(
            self,
            "MyInstanceIpAddrOutput",
            value = my_instance.instance_public_ip,
            description = "Public Ip Addr for Bastion Host",
        )

        # DBの作成
        my_rds = rds.DatabaseInstance(
            self,
            "MyRdsInstance",
            engine = rds.DatabaseInstanceEngine.mysql(
                version = rds.MysqlEngineVersion.VER_8_0_43,
            ),
            vpc = my_vpc,
            subnet_group = my_subnet_group,
            security_groups = [my_sg_for_rds],
            instance_type = ec2.InstanceType.of(
                ec2.InstanceClass.T4G,
                ec2.InstanceSize.MICRO,
            ),
            instance_identifier = "my-schedule-app-db",
            publicly_accessible = False,
            allocated_storage = 20,
            deletion_protection = False,
            credentials = rds.Credentials.from_generated_secret("admin"),
            database_name = "my_schedule_app_db",
        )

        # pymysqlをカスタムLayerとして用意
        pymysql_layer = aws_lambda.LayerVersion(
            self,
            "PymysqlLayer",
            code = aws_lambda.Code.from_asset("./src/backend/layer2"),
            compatible_runtimes = [aws_lambda.Runtime.PYTHON_3_13],
            description = "pymysql package for My Schedule App",
        )

        # カスタムLayerの作成
        mypackage_layer = aws_lambda.LayerVersion(
            self,
            "MyPackageLayer",
            code = aws_lambda.Code.from_asset("./src/backend/layer"),
            compatible_runtimes = [aws_lambda.Runtime.PYTHON_3_13],
            description = "My custom package layer for My Schedule App",
        )

        # Lambda 関数の作成
        lambda_get_calendar = aws_lambda.Function(
            self,
            "LambdaGetCalendar",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler =  "get_calendar.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/get_calendar"),
            timeout =  Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        lambda_get_detail = aws_lambda.Function(
            self,
            "LambdaGetDetail",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler = "get_detail.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/get_detail"),
            timeout = Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        lambda_get_event = aws_lambda.Function(
            self,
            "LambdaGetEvent",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler = "get_event.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/get_event"),
            timeout = Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        lambda_add_event = aws_lambda.Function(
            self,
            "LambdaAddEvent",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler = "add_event.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/add_event"),
            timeout = Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        lambda_delete_event = aws_lambda.Function(
            self,
            "LambdaDeleteEvent",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler = "delete_event.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/delete_event"),
            timeout = Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        lambda_update_event = aws_lambda.Function(
            self,
            "LambdaUpdateEvent",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler = "update_event.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/update_event"),
            timeout = Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        lambda_init_db = aws_lambda.Function(
            self,
            "LambdaInitDB",
            runtime = aws_lambda.Runtime.PYTHON_3_13,
            handler = "init_db.lambda_handler",
            code = aws_lambda.Code.from_asset("./src/backend/functions/init_db"),
            timeout = Duration.seconds(30),
            vpc = my_vpc,
            vpc_subnets = my_subnet_for_lambda,
            security_groups = [my_sg_for_lambda],
            # allow_public_subnet = True,
            layers=[pymysql_layer, mypackage_layer],
        )

        # 関数をリストにまとめる
        lambdas = [
            lambda_get_calendar,
            lambda_get_detail,
            lambda_get_event,
            lambda_add_event,
            lambda_delete_event,
            lambda_update_event,
            lambda_init_db,
        ]

        # 生成されたSecretsManagerのSecret_idを取得
        my_secret = my_rds.secret
        
        for fn in lambdas:
            my_secret.grant_read(fn)

        # SSMパラメータストアに値を代入する
        # CDKで作成した場合、SecretsManagerにすべて含まれてるので、そっち使ったほうがよいけど、、、
        rds_host = my_rds.db_instance_endpoint_address
        my_secret_id = my_rds.secret.secret_name

        ssm.StringParameter(
            self,
            "RdsHost",
            parameter_name="/my_schedule_app/rds_host",
            string_value = rds_host,
        )

        ssm.StringParameter(
            self,
            "RdsDatabase",
            parameter_name = "/my_schedule_app/rds_database",
            string_value = "my_schedule_app_db",
        )

        ssm.StringParameter(
            self,
            "MySecretId",
            parameter_name="/my_schedule_app/secret_id",
            string_value = my_secret_id,
        )

        ssm.StringParameter(
            self,
            "MyRegion",
            parameter_name = "/my_schedule_app/region_name",
            string_value = self.region,
        )

        # 祝日情報csvの保存bucket名
        ssm.StringParameter(
            self,
            "MyDataBucket",
            parameter_name = "/my_schedule_app/data_bucket",
            string_value = data_bucket.bucket_name,
        )

        # SSM パラメータストアのパラメータへのアクセス権限を付与
        my_custom_iam_policy_statement = iam.PolicyStatement(
            effect = iam.Effect.ALLOW,
            actions = ["ssm:GetParameter","ssm:GetParameters"],
            resources = [f"arn:aws:ssm:{self.region}:{self.account}:parameter/my_schedule_app/*"],
        )

        for fn in lambdas:
            fn.role.add_to_policy(my_custom_iam_policy_statement)

        # init_db.pyにS3バケットへのアクセス権限を付与
        data_bucket.grant_read(lambda_init_db)

        # Cognitoユーザープールの作成
        my_user_pool = cognito.UserPool(
            self,
            "MyUserPool",
            user_pool_name = "MyScheduleAppUserPool",
            self_sign_up_enabled = False,
            sign_in_aliases = cognito.SignInAliases(
                username = True,
                email = False,
            ),
            auto_verify = cognito.AutoVerifiedAttrs(email=False),
        )

        CfnOutput(
            self,
            "MyUserPoolNameOutput",
            value = my_user_pool.user_pool_id,
        )

        # ユーザープールクライアントの作成
        my_user_pool_client = cognito.UserPoolClient(
            self,
            "MyUserPoolClient",
            user_pool = my_user_pool,
            generate_secret = False,
            auth_flows = cognito.AuthFlow(
                user_password = True,
                user_srp = True,
                admin_user_password = True,
            ),
        )

        # 出力
        CfnOutput(self, "UserPoolId", value = my_user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value = my_user_pool_client.user_pool_client_id)

        my_cognito_info = f"""
        window.CognitoConfig = {{
            UserPoolId: '{my_user_pool.user_pool_id}',
            UserPoolClientId: '{my_user_pool_client.user_pool_client_id}',
            Region: '{self.region}'
        }}

        """

        # オーソライザー作成
        my_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, 
            "MyAuthorizer",
            cognito_user_pools=[my_user_pool]
        )

        # API Gateway の作成
        my_api = apigw.RestApi(
            self,
            "MyCdkApi",
            default_cors_preflight_options = apigw.CorsOptions(
                allow_origins = apigw.Cors.ALL_ORIGINS,
                allow_methods = apigw.Cors.ALL_METHODS,
            ),
            endpoint_configuration = apigw.EndpointConfiguration(types=[apigw.EndpointType.REGIONAL]),
            deploy_options = apigw.StageOptions(
                stage_name = "prod",
                throttling_rate_limit = 10,
                throttling_burst_limit = 20,
            )
        )

        my_api_gateway_info = f"""
        export const API_GATEWAY_URL = '{my_api.url_for_path()}';
        """

        # HTMLファイルアップロード
        html_upload = s3_deployment.BucketDeployment(
            self,
            "HTMLUpload",
            sources = [
                s3_deployment.Source.asset("./src/frontend"),
                s3_deployment.Source.data("js/config/cognito-config.js", my_cognito_info),
                s3_deployment.Source.data("js/config/api-gateway-config.js", my_api_gateway_info),
            ],
            destination_bucket= website_bucket,
        )

        # --- リソースとメソッドの追加 ---
        # my_test_resource = my_api.root.add_resource("my-test")
        get_calendar_resource = my_api.root.add_resource("get-calendar")
        get_detail_resource = my_api.root.add_resource("get-detail")
        get_event_resource = my_api.root.add_resource("get-event")
        add_event_resource = my_api.root.add_resource("add-event")
        delete_event_resource = my_api.root.add_resource("delete-event")
        update_event_resource = my_api.root.add_resource("update-event")

        get_calendar_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_get_calendar),
            authorizer=my_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # 他のリソースにも同様にメソッドを追加すること
        get_detail_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_get_detail),
            authorizer=my_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        get_event_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_get_event),
            authorizer = my_authorizer,
            authorization_type = apigw.AuthorizationType.COGNITO,
        )

        add_event_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_add_event),
            authorizer = my_authorizer,
            authorization_type = apigw.AuthorizationType.COGNITO,
        )

        delete_event_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_delete_event),
            authorizer = my_authorizer,
            authorization_type = apigw.AuthorizationType.COGNITO,
        )

        update_event_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_update_event),
            authorizer = my_authorizer,
            authorization_type = apigw.AuthorizationType.COGNITO,
        )

        # lambda_init_dbを実行する
        provider = cr.Provider(
            self,
            "LambdaInitDbProvider",
            on_event_handler = lambda_init_db,
        )

        CustomResource(
            self,
            "CustomResource",
            service_token = provider.service_token
        )

       