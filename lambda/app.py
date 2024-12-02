import json
import boto3
import os
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Helper function to get environment variables with error handling
def get_env_var(var_name):
    value = os.getenv(var_name)
    if value is None:
        logger.error(f"Environment variable {var_name} is not set.")
        raise EnvironmentError(f"Required environment variable {var_name} is not set.")
    return value

# Read configurations from environment variables
INSTANCE_ID = get_env_var('CONNECT_INSTANCE_ID')
SECURITY_PROFILE_ID = get_env_var('CONNECT_SECURITY_PROFILE_ID')
ROUTING_PROFILE_ID = get_env_var('CONNECT_ROUTING_PROFILE_ID')


# Initialize Amazon Connect client
client = boto3.client('connect')

def lambda_handler(event, context):
    """
    Main handler for Lambda function
    Processes both Okta verification requests and user creation events
    """
    try:
        logger.info("Received event: %s", json.dumps(event))
        # Determine HTTP method and route accordingly
        http_method = get_http_method(event)
        if http_method == "POST":
            return create_amazon_connect_user(event)
        elif http_method == "GET":
            return okta_one_time_verification_handler(event)
        else:
            logger.warning(f"Unsupported HTTP method: {http_method}")
            return method_not_allowed(http_method)

    except KeyError as e:
        logger.error(f"KeyError: {str(e)}")
        return client_error_response(str(e))
    except EnvironmentError as e:
        logger.error(f"EnvironmentError: {str(e)}")
        return internal_server_error(f"Environment variable error: {str(e)}")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return internal_server_error()


def get_http_method(event):
    """Extracts HTTP method from the event, raising KeyError if missing."""
    try:
        return event['requestContext']['http'].get('method')
    except KeyError:
        raise KeyError("HTTP method not found in event")


def create_amazon_connect_user(event):
    try:
        users = user_info_parser(json.loads(event['body']))
        logger.info("User data extracted: %s", users)

        if not users:
            raise ValueError("No valid user information found in data")

        for user in users:
            username = user['alternate_id']
            first_name = user['fName']
            last_name = user['lName']

            # Check for duplicate user
            if is_duplicate_user(username):
                # Don't return error to the client, only log the duplicate user in logs.
                logger.warning(f"User with username '{username}' already exists.")


            # For the detailed parameters of creating user, you can refer the following document
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/connect.html#Connect.Client.create_user
            response = client.create_user(
                Username=username,
                IdentityInfo={
                    'FirstName': first_name,
                    'LastName': last_name
                },
                PhoneConfig={
                    'PhoneType': 'SOFT_PHONE'
                },
                SecurityProfileIds=[SECURITY_PROFILE_ID],
                RoutingProfileId=ROUTING_PROFILE_ID,
                InstanceId=INSTANCE_ID
            )
            logger.info(f"Create UserId {response['UserId']} and UserArn {response['UserArn']}")
            return success_response({'message': 'Connect user created successfully'})

    except ValueError as ve:
        logger.error(f"Data extraction error: {ve}")
        return client_error_response(str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in user creation: {e}")
        return internal_server_error()


def is_duplicate_user(username):
    """Checks if a user with the given username already exists."""
    try:
        logger.info(f"Checking for duplicate user: {username}")
        response = client.list_users(InstanceId=INSTANCE_ID)
        users = response.get('UserSummaryList', [])

        for user in users:
            if user['Username'] == username:
                logger.info(f"Duplicate user found: {username}")
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking for duplicate user: {e}")
        raise


def okta_one_time_verification_handler(event):
    """
    Handle Okta's one-time verification request
    Returns the verification code in the required format
    """
    try:
        verification_code = event["multiValueHeaders"]['X-Okta-Verification-Challenge'][0]
        if not verification_code:
            logger.warning("Okta verification challenge header missing")
            return client_error_response('x-okta-verification-challenge header not found')

        logger.info(f"Verification challenge received: {verification_code}")
        return success_response({'verification': verification_code})

    except KeyError as e:
        logger.error(f"KeyError: {str(e)}")
        return client_error_response(str(e))


def user_info_parser(user_add_event):
    """
    Parse Okta event to extract user information
    Returns a list of users to be created in Amazon Connect
    """
    logger.info("Calling user parser")
    user_info_list = []

    try:
        events = user_add_event["data"]["events"]
        if not events:
            raise ValueError("No events found in data")

        # Process each event
        for event in events:
            user_info_dic = {}
            event_target = event["target"]
            for obj in event_target:
                # Extract user information
                if obj["type"] == "User":
                    user_info_dic["alternate_id"] = obj["alternateId"]
                    user_info_dic["display_name"] = obj["displayName"]

                    # Parse names into first name and last name
                    names = obj["displayName"].split(' ')
                    user_info_dic["fName"] =  names[0] if names else 'N/A'
                    user_info_dic["lName"] = names[-1] if len(names) > 1 else 'N/A'

                    user_info_list.append(user_info_dic)

        # Check if user_info was populated
        if not user_info_list:
            raise ValueError("No valid user information found in data")

        return user_info_list

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error extracting user info: {e}")
        raise


# Utility response functions
def success_response(body):
    return {'statusCode': 200, 'body': json.dumps(body)}


def client_error_response(message):
    return {'statusCode': 400, 'body': json.dumps({'error': message})}


def method_not_allowed(method):
    return {
        'statusCode': 405,
        'body': json.dumps({'error': f'Method {method} not allowed'})
    }


def internal_server_error(message="Internal server error"):
    return {'statusCode': 500, 'body': json.dumps({'error': message})}