#!/bin/bash

# Prompt the user to choose the environment
echo "Choose the environment: (1) for OncoSTR, (2) for OncoFEM)"
read env_choice

if [[ "$env_choice" == "1" ]]; then
  conda activate oncostr
elif [[ "$env_choice" == "2" ]]; then
  conda activate oncofem
else
  echo "Invalid choice. Please choose either '1' for OncoSTR or '2' for OncoFEM."
  exit 1
fi

python3 -m pip install .
echo "Installation of oncostr is completed successfully!"
echo "Please open a pyhton terminal and run 'import oncostr' to check if oncostr is installed correctly."
exit 0