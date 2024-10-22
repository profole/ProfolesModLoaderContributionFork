#!/bin/bash

if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed. Please install Python3 and try again."
    exit
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
REQUIRED_VERSION="3.12"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "Python version must be at least 3.12. Current version: $PYTHON_VERSION"
    exit 1
fi

VENV_DIR="venv"
NEW_ENV=0

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found, creating a new one..."

    python3 -m venv "$VENV_DIR"
    
    if [ ! -d "$VENV_DIR" ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi

    echo "Virtual environment created."
    NEW_ENV=1
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

if [ $NEW_ENV -eq 1 ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

echo "Running the application..."
python3 main.py

deactivate
echo "Application finished."