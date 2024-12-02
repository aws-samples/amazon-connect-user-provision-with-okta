import json
import logging
import boto3
import os

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Amazon Connect client
client = boto3.client('connect')


# Helper function to get environment variables with error handling
def get_env_var(var_name):
    value = os.getenv(var_name)
    if value is None:
        logger.error(f"Environment variable {var_name} is not set.")
        raise EnvironmentError(f"Required environment variable {var_name} is not set.")
    return value


# Environment variables with validation
INSTANCE_ID = get_env_var('INSTANCE_ID')
ROUTING_PROFILE_ID = get_env_var('ROUTING_PROFILE_ID')
SECURITY_PROFILE_ID = get_env_var('SECURITY_PROFILE_ID')


def lambda_handler(event, context):
    """Main handler for Lambda function."""
    try:
        logger.info("Received event: %s", json.dumps(event))

        # Determine HTTP method and route accordingly
        http_method = get_http_method(event)
        if http_method == "POST":
            return create_connect_user(event)
        elif http_method == "GET":
            return okta_verification_challenge(event)
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


def create_connect_user(event):
    """Handles the creation of a Connect user for POST requests."""

    try:
        user_data = extract_user_info(json.loads(event['body']))
        logger.info("User data extracted: %s", user_data)

        if not user_data:
            raise ValueError("No valid user information found in data")

        username = user_data[0]['alternateId']
        first_name = user_data[0]['fName']
        last_name = user_data[0]['lName']

        # Check for duplicate user
        if is_duplicate_user(username):
            logger.warning(f"User with username '{username}' already exists.")
            return client_error_response(f"User with username '{username}' already exists.")

        # Add Connect user
        response = client.create_user(
            Username=username,
            IdentityInfo={
                'FirstName': first_name,
                'LastName': last_name
            },
            PhoneConfig={'PhoneType': 'SOFT_PHONE'},
            SecurityProfileIds=[SECURITY_PROFILE_ID],
            RoutingProfileId=ROUTING_PROFILE_ID,
            InstanceId=INSTANCE_ID
        )

        logger.info("User was created.")
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


def extract_user_info(event_data):
    """ Parses and extracts user information from event data. """
    logger.info("Calling user extract")
    user_info = []

    try:
        # Retrieve events from data
        events = event_data.get('data', {}).get('events', [])
        if not events:
            raise ValueError("No events found in data")

        # Process each event
        for event in events:
            for target in event.get('target', []):
                target_type = target.get('type')
                display_name = target.get('displayName')

                if target_type == "User":
                    # Extract user information
                    names = display_name.split(' ')
                    user_info.append({
                        'displayName': display_name,
                        'alternateId': target.get('alternateId', 'N/A'),
                        'fName': names[0] if names else 'N/A',
                        'lName': names[-1] if len(names) > 1 else 'N/A'
                    })

        # Check if user_info was populated
        if not user_info:
            raise ValueError("No valid user information found in data")

        return user_info

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error extracting user info: {e}")
        raise


def okta_verification_challenge(event):
    """Handles Okta verification challenge for GET requests."""
    try:
        challenge = event.get('headers', {}).get('x-okta-verification-challenge')
        if not challenge:
            logger.warning("Okta verification challenge header missing")
            return client_error_response('x-okta-verification-challenge header not found')

        logger.info(f"Verification challenge received: {challenge}")
        return success_response({'verification': challenge})
    except KeyError as e:
        logger.error(f"KeyError: {str(e)}")
        return client_error_response(str(e))


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