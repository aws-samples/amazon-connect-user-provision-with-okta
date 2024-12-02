import json
import boto3
import os
from botocore.exceptions import ClientError

print('Loading function')

# Read configurations from environment variables
APP_NAME = os.environ['OKTA_APP_NAME']
GROUP_NAME = os.environ['OKTA_GROUP_NAME']
APP_MEMBERSHIP_ADD_EVENT = os.environ['OKTA_APP_MEMBERSHIP_ADD_EVENT']
GROUP_MEMBERSHIP_ADD_EVENT = os.environ['OKTA_GROUP_MEMBERSHIP_ADD_EVENT']

# Initialize Amazon Connect client
client = boto3.client('connect')

def lambda_handler(event, context):
    """
    Main handler for Lambda function
    Processes both Okta verification requests and user creation events
    """
    # Handle Okta one-time verification request
    if event['httpMethod'] == "GET":
        print("One-Time Okta Verification Request")
        return _okta_one_time_verification_handler(event)

    # Process Okta user event
    event_hook_obj = json.loads(event['body'])
    user_list = _user_info_parser(event_hook_obj)
    print("user list is: ", user_list)

    # Get Connect configurations from environment variables
    security_profile_ids = os.environ['CONNECT_SECURITY_PROFILE_IDS'].split(",")
    routing_profile_id = os.environ['CONNECT_ROUTING_PROFILE_ID']
    instance_id = os.environ['CONNECT_INSTANCE_ID']
    
    # Create users in Amazon Connect if user list is not empty
    if user_list:
        _create_amazon_connect_user(user_list, security_profile_ids, routing_profile_id, instance_id)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        }
    }

def _okta_one_time_verification_handler(event):
    """
    Handle Okta's one-time verification request
    Returns the verification code in the required format
    """
    verification_code = event["multiValueHeaders"]['X-Okta-Verification-Challenge'][0]
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "verification": verification_code
        })
    }

def _user_info_parser(user_add_event):
    """
    Parse Okta event to extract user information
    Returns a list of users to be created in Amazon Connect
    """
    events = user_add_event["data"]["events"]
    user_info_list = []

    for event in events:
        event_type = event["eventType"]
        user_info_dic = {}

        if event_type == APP_MEMBERSHIP_ADD_EVENT or GROUP_MEMBERSHIP_ADD_EVENT:
            event_target = event["target"]
            for obj in event_target:
                # Extract user information
                if obj["type"] == "User":
                    user_info_dic["alternate_id"] = obj["alternateId"]
                    user_info_dic["display_name"] = obj["displayName"]
                    user_info_list.append(user_info_dic)

                # Skip events that don't match the configured group or app
                if obj["type"] == "UserGroup" and obj["displayName"] != GROUP_NAME:
                    user_info_list = []
                    print("Skipping event: Group name mismatch")
                if obj["type"] == "AppInstance" and obj["displayName"] != APP_NAME:
                    user_info_list = []
                    print("Skipping event: App name mismatch")

    return user_info_list

def _create_amazon_connect_user(users, security_profile_ids, routing_profile_id, instance_id):
    """
    Create users in Amazon Connect with the specified profiles and settings
    """
    for user in users:
        alternative_id = user['alternate_id']
        try:
            response = client.create_user(
                Username=alternative_id,
                IdentityInfo={
                    'FirstName': 'Hello',
                    'LastName': 'World'
                },
                PhoneConfig={
                    'PhoneType': 'SOFT_PHONE'
                },
                SecurityProfileIds=security_profile_ids,
                RoutingProfileId=routing_profile_id,
                InstanceId=instance_id
            )
            print(f"Successfully created user: UserId {response['UserId']}, UserArn {response['UserArn']}")
        except ClientError as e:
            print(f"Failed to create user {alternative_id}: {str(e)}")
