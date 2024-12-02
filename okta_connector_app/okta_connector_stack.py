from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
import uuid

class OktaConnectorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get parameters with default values
        security_profile_ids = self.node.try_get_context('connect-security-profile-ids')
        routing_profile_id = self.node.try_get_context('connect-routing-profile-id')
        instance_id = self.node.try_get_context('connect-instance-id')
        enable_auth = self.node.try_get_context('enable-auth')

        # Validate required parameters
        if not all([security_profile_ids, routing_profile_id, instance_id]):
            raise ValueError(
                "Missing required parameters. Please provide: "
                "connect-security-profile-ids, connect-routing-profile-id, and connect-instance-id"
            )

        # Create API key secret if auth is enabled
        api_key = None
        api_key_secret = None
        if enable_auth:
            # Generate random API key
            api_key = str(uuid.uuid4())

            # Create secret in Secrets Manager
            api_key_secret = secretsmanager.Secret(
                self, 'ApiKeySecret',
                secret_string=api_key,
                removal_policy=RemovalPolicy.DESTROY  # 自動清理，視需求調整
            )

        # Create Lambda function
        lambda_function = _lambda.Function(
            self, 'OktaConnectorFunction',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='app.lambda_handler',
            code=_lambda.Code.from_asset('lambda'),
            environment={
                # Connect configurations
                "CONNECT_SECURITY_PROFILE_IDS": security_profile_ids,
                "CONNECT_ROUTING_PROFILE_ID": routing_profile_id,
                "CONNECT_INSTANCE_ID": instance_id,
                "SECRET_ARN": api_key_secret.secret_arn if enable_auth else ""
            }
        )

        # Add Secrets Manager permissions if auth is enabled
        if enable_auth:
            api_key_secret.grant_read(lambda_function)

        # Add Connect permissions
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "connect:CreateUser",
                    "connect:ListUsers"
                ],
                resources=[
                    # For CreateUser and DeleteUser operations
                    f"arn:aws:connect:*:{self.account}:instance/{instance_id}/user/*",
                ]
            )
        )
        # Setup API Gateway
        api = apigw.RestApi(
            self, 'OktaConnectorApi',
            rest_api_name='Okta Integration API'
        )

        # Create API integration and methods
        integration = apigw.LambdaIntegration(lambda_function)
        create_user_resource = api.root.add_resource('create_user')
        create_user_resource.add_method('POST', integration)
        create_user_resource.add_method('GET', integration)

        # Add CloudFormation outputs
        CfnOutput(
            self, "ApiUrl",
            value=f"{api.url}create_user",
            description="API Gateway endpoint URL for OKTA event hook"
        )

        CfnOutput(
            self, "LambdaArn",
            value=lambda_function.function_arn,
            description="Lambda function ARN",
            export_name="OktaConnectorLambdaArn"
        )

        CfnOutput(
            self, "ApiId",
            value=api.rest_api_id,
            description="API Gateway ID",
            export_name="OktaConnectorApiId"
        )

        if enable_auth:
            CfnOutput(
                self, "ApiKey",
                value=api_key,
                description="API Key (store securely)"
            )