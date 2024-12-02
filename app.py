#!/usr/bin/env python3
from aws_cdk import App
from okta_connector_app.okta_connector_stack import OktaConnectorStack

app = App()

# Define required parameters with their descriptions and examples
required_params = {
    'connect-security-profile-ids': {
        'description': 'Comma-separated security profile IDs',
        'example': '27a6dbc8-4927-4ba9-abd8-0aa7f5123456'
    },
    'connect-routing-profile-id': {
        'description': 'Routing profile ID',
        'example': '6a0a6c65-69fb-1234-abcd-f8666ac189cb'
    },
    'connect-instance-id': {
        'description': 'Connect instance ID',
        'example': 'd77493ae-0342-f5sv-adc2-a0ebe5a2b2a7'
    }
}

# Check for missing parameters
missing_params = [
    param for param in required_params
    if not app.node.try_get_context(param)
]

# If any required parameters are missing, raise an error with usage instructions
if missing_params:
    error_message = "\nError: Missing required parameters\n"
    error_message += "\nRequired parameters:\n"

    # List all missing parameters with their descriptions
    for param in missing_params:
        error_message += f"  - {param}: {required_params[param]['description']}\n"

    # Provide usage examples
    error_message += "\nUsage examples:\n"

    # Example 1: Command line usage
    error_message += "\n1. Using command line:\n"
    error_message += "cdk deploy \\\n"
    for param in required_params:
        error_message += f"  -c {param}={required_params[param]['example']} \\\n"

    # Example 2: cdk.json configuration
    error_message += "\n2. Or add to cdk.json:\n"
    error_message += "{\n"
    error_message += '  "context": {\n'
    for param in required_params:
        error_message += f'    "{param}": "{required_params[param]["example"]}",\n'
    error_message += "  }\n"
    error_message += "}\n"

    raise ValueError(error_message)

# Create the stack and synthesize the CloudFormation template
OktaConnectorStack(app, "OktaConnectorStack")
app.synth()
