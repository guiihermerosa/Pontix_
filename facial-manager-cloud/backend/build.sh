#!/bin/bash

# Build script for Render deployment

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating database..."
python migrations.py create

echo "Build completed successfully!"
