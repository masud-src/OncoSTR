#!/bin/bash

# Function to install packages for Linux
install_linux() {
    echo "Detected Linux OS. Proceeding with installation."
    sudo apt update
    sudo apt upgrade -y
    sudo apt install -y build-essential python3-pip git
}

# Function to install packages for macOS
install_macos() {
    echo "Detected macOS. Proceeding with installation."
    # Check if Homebrew is installed
    if ! command -v brew &>/dev/null; then
        echo "Homebrew is not installed. Installing Homebrew."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo "Homebrew installed successfully."
    fi

    brew update
    brew upgrade
    brew install \
        python3 \
        git

    # Ensure command-line tools are installed
    xcode-select --install 2>/dev/null || echo "Command line tools already installed."
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    install_linux
elif [[ "$OSTYPE" == "darwin"* ]]; then
    install_macos
else
    echo "Unsupported operating system: $OSTYPE"
    exit 1
fi

git clone https://github.com/masud-src/OncoSTR/
cd OncoSTR
python3 create_conda_environment.py
conda activate oncostr
cd ..
curl -O https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py
python3 fslinstaller.py
cd OncoSTR
echo "Installation of prerequisites is completed successfully!"
echo "Some changes require the terminal to be restarted."
echo "Please close and reopen your terminal to apply the changes."
exit 0
