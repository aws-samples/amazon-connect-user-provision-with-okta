from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class MyOktaConnectStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get parameters with default values
        okta_app_name = self.node.try_get_context('okta-app-name')
        okta_group_name = self.node.try_get_context('okta-group-name')
        security_profile_ids = self.node.try_get_context('connect-security-profile-ids')
        routing_profile_id = self.node.try_get_context('connect-routing-profile-id')
        instance_id = self.node.try_get_context('connect-instance-id')

        # Validate required parameters
        if not all([security_profile_ids, routing_profile_id, instance_id]):
            raise ValueError(
                "Missing required parameters. Please provide: "
                "connect-security-profile-ids, connect-routing-profile-id, and connect-instance-id"
            )

        # Create Lambda function
        lambda_function = _lambda.Function(
            self, 'OktaConnectFunction',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='app.lambda_handler',
            code=_lambda.Code.from_asset('lambda'),
            environment={
                # Okta configurations
                "OKTA_APP_NAME": okta_app_name,
                "OKTA_GROUP_NAME": okta_group_name,
                "OKTA_APP_MEMBERSHIP_ADD_EVENT": "application.user_membership.add",
                "OKTA_GROUP_MEMBERSHIP_ADD_EVENT": "group.user_membership.add",

                # Connect configurations
                "CONNECT_SECURITY_PROFILE_IDS": security_profile_ids,
                "CONNECT_ROUTING_PROFILE_ID": routing_profile_id,
                "CONNECT_INSTANCE_ID": instance_id,
            }
        )

        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "connect:CreateUser",
                    "connect:DeleteUser"
                ],
                resources=[
                    # For CreateUser and DeleteUser operations
                    f"arn:aws:connect:*:{self.account}:instance/{instance_id}/user/*",
                ]
            )
        )
        # Setup API Gateway
        api = apigw.RestApi(
            self, 'OktaConnectApi',
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
            description="API Gateway endpoint URL"
        )

        CfnOutput(
            self, "LambdaArn",
            value=lambda_function.function_arn,
            description="Lambda function ARN",
            export_name="OktaConnectLambdaArn"
        )

        CfnOutput(
            self, "ApiId",
            value=api.rest_api_id,
            description="API Gateway ID",
            export_name="OktaConnectApiId"
        )