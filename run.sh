#!/bin/bash

# Change to the directory where this script is located
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -f "env/bin/activate" ]; then
    echo "Error: Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
if [ -f "env/bin/activate" ]; then
    source env/bin/activate
    if [ $? -ne 0 ]; then
        echo "Error: Failed to activate virtual environment"
        exit 1
    fi
else
    echo "Error: Virtual environment activation script not found"
    exit 1
fi

# Run the Python script
python3 main.py