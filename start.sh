#!/bin/bash

echo "--- Link Preview Micro-SaaS Setup ---"

# 1. Check if virtual environment exists, if not, create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate the environment
echo "Activating environment..."
source venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 4. Run the server
echo "Starting API Server..."
echo "Your API is running at: http://127.0.0.1:8000"
echo "Access the Swagger Docs at: http://127.0.0.1:8000/docs"
python main.py
