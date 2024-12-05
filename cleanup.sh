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


# Generate the cdk deploy command
DEPLOY_COMMAND="cdk destroy"

# Execute cdk deploy
echo "Running cdk destroy..."
eval $DEPLOY_COMMAND
if [[ $? -ne 0 ]]; then
  echo "Error: cdk destroy failed."
  exit 1
fi

# Confirm successful completion
echo "cdk destroy completed successfully."
