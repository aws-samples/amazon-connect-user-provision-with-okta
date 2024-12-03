#!/bin/bash

# Step 1: Create and activate a Python virtual environment
echo "Setting up Python virtual environment..."

# Check if virtualenv already exists
if [[ ! -d ".venv" ]]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
  if [[ $? -ne 0 ]]; then
    echo -e "\e[31mError: Failed to create virtualenv. Make sure Python 3 is installed.\e[0m"
    exit 1
  fi
else
  echo "Virtualenv already exists."
fi

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

# Step 2: Install required dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [[ $? -ne 0 ]]; then
  echo -e "\e[31mError: Failed to install dependencies. Make sure requirements.txt exists.\e[0m"
  deactivate
  exit 1
fi
