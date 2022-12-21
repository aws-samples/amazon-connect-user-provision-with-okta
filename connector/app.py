#
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy of this
#  software and associated documentation files (the "Software"), to deal in the Software
#  without restriction, including without limitation the rights to use, copy, modify,
#  merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
import json
import boto3
import configparser
from botocore.exceptions import ClientError

print('Loading function')


config = configparser.ConfigParser()
config.read('config.ini')

#OKTA config
APP_NAME = config['OKTA']['APP_NAME']
GROUP_NAME = config['OKTA']['GROUP_NAME']
APP_MEMBERSHIP_ADD_EVENT = config['OKTA']['APP_MEMBERSHIP_ADD_EVENT']
GROUP_MEMBERSHIP_ADD_EVENT = config['OKTA']['GROUP_MEMBERSHIP_ADD_EVENT']

# Amazon Connect client
client = boto3.client('connect')


def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))

    # For One-Time Verification Request
    # https://developer.okta.com/docs/concepts/event-hooks/#one-time-verification-request
    if event['httpMethod'] == "GET":
        print("One-Time Okta Verification Request")
        return _okta_one_time_verification_handler(event)

    # Parse okta add user event
    event_hook_obj = json.loads(event['body'])
    user_list = _user_info_parser(event_hook_obj)
    print("user list is: ", user_list)

    # Create mapping users on Amazon Connect
    security_profile_ids = config['Connect'].get('SECURITY_PROFILE_IDS').split(",")
    routing_profile_id = config['Connect']['ROUTING_PROFILE_ID']
    instance_id = config['Connect']['INSTANCE_ID']
    if user_list:
        _create_amazon_connect_user(user_list, security_profile_ids, routing_profile_id, instance_id)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        }
    }


def _okta_one_time_verification_handler(event):
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
    events = user_add_event["data"]["events"]
    user_info_list = []

    for event in events:
        event_type = event["eventType"]
        user_info_dic = {}

        if event_type == APP_MEMBERSHIP_ADD_EVENT or GROUP_MEMBERSHIP_ADD_EVENT:
            event_target = event["target"]
            for obj in event_target:
                if obj["type"] == "User":
                    user_info_dic["alternate_id"] = obj["alternateId"]
                    user_info_dic["display_name"] = obj["displayName"]
                    user_info_list.append(user_info_dic)

                # Skip events which doesn't match defined APP_NAME or GROUP_NAME, and reset the user_info_list
                if obj["type"] == "UserGroup" and obj["displayName"] != GROUP_NAME:
                    user_info_list = []
                    print("skip the event")
                if obj["type"] == "AppInstance" and obj["displayName"] != APP_NAME:
                    user_info_list = []
                    print("skip the event")

    return user_info_list


def _create_amazon_connect_user(users, security_profile_ids, routing_profile_id, instance_id):
    for user in users:
        alternative_id = user['alternate_id']
        display_name = user['display_name']
        security_profile_ids = security_profile_ids
        routing_profile_id = routing_profile_id
        instance_id = instance_id

        # For the detailed parameters of creating user, you can refer the following document
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/connect.html#Connect.Client.create_user
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
            print(f"Create UserId {response['UserId']} and UserArn {response['UserArn']}")
        except ClientError as e:
            print(e)
            print(f"Create UserId {alternative_id} Failed.")
