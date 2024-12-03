#!/bin/bash

# Activate the virtualenv
echo "Activating virtualenv..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  # Windows
  .venv\Scripts\activate.bat
else
  # MacOS/Linux
  source .venv/bin/activate
fi

if [[ $? -ne 0 ]]; then
  echo -e "\e[31mError: Failed to activate virtualenv.\e[0m"
  exit 1
fi

# Prompt the user to provide required parameters
echo "Please provide the required parameters:"
printf "\n"

# Prompt for connect-security-profile-ids
echo "connect-security-profile-ids - The security profile for the provisioning agents"
read -p "Enter connect-security-profile-ids(ex: 12345678-1234-2345-abd8-0aa7f5b46852): " CONNECT_SECURITY_PROFILE_IDS

printf "\n"
# Prompt for connect-routing-profile-id
echo "connect-routing-profile-id - The profile for the provisioning agents"
read -p "Enter connect-routing-profile-id(ex: 87654321-69fb-43b6-a5e6-f8666ac189cb): " CONNECT_ROUTING_PROFILE_ID

printf "\n"
# Prompt for connect-instance-id
echo "connect-instance-id - Your Amazon Connect Instance ID"
read -p "Enter connect-instance-id(ex: bcdefgh-0122-4131-adc2-a0ebe5a2b2a7): " CONNECT_INSTANCE_ID

printf "\n"
# Prompt the user to optionally provide a profile
echo "Optional: Provide an AWS CLI profile for deployment (leave blank to use the default profile)"
read -p "Enter AWS CLI profile (or press Enter to skip): " AWS_PROFILE


printf "\n"
# Validate if all required parameters are provided
if [[ -z "$CONNECT_SECURITY_PROFILE_IDS" || -z "$CONNECT_ROUTING_PROFILE_ID" || -z "$CONNECT_INSTANCE_ID" ]]; then
  echo -e "Error: All parameters are required. Please run the script again and provide all inputs."
  exit 1
fi

# Display the received parameters
echo
echo "Parameters received:"
echo "  connect-security-profile-ids: $CONNECT_SECURITY_PROFILE_IDS"
echo "  connect-routing-profile-id: $CONNECT_ROUTING_PROFILE_ID"
echo "  connect-instance-id: $CONNECT_INSTANCE_ID"
if [[ -n "$AWS_PROFILE" ]]; then
  echo "  AWS CLI profile: $AWS_PROFILE"
else
  echo "  AWS CLI profile: (default profile)"
fi
echo

# Prompt the user to confirm the parameters
read -p "Are these parameters correct? (y/n): " CONFIRM
if [[ "$CONFIRM" != "y" ]]; then
  echo "Exiting. Please rerun the script and provide the correct parameters."
  exit 1
fi

# Construct the profile argument if a profile is provided
PROFILE_ARG=""
if [[ -n "$AWS_PROFILE" ]]; then
  PROFILE_ARG="--profile $AWS_PROFILE"
fi

# Run cdk bootstrap
echo "Running cdk bootstrap..."
cdk bootstrap $PROFILE_ARG
if [[ $? -ne 0 ]]; then
  echo "Error: cdk bootstrap failed."
  exit 1
fi

# Generate the cdk deploy command
DEPLOY_COMMAND="cdk deploy $PROFILE_ARG \
  -c connect-security-profile-ids=$CONNECT_SECURITY_PROFILE_IDS \
  -c connect-routing-profile-id=$CONNECT_ROUTING_PROFILE_ID \
  -c connect-instance-id=$CONNECT_INSTANCE_ID"

# Display the generated deploy command
echo "Generated deploy command:"
echo "$DEPLOY_COMMAND"
echo

# Execute cdk deploy
echo "Running cdk deploy..."
eval $DEPLOY_COMMAND
if [[ $? -ne 0 ]]; then
  echo "Error: cdk deploy failed."
  exit 1
fi

# Confirm successful completion
echo "cdk bootstrap and deploy completed successfully."
