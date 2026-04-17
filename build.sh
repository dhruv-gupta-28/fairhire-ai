#!/bin/bash
# Exit on error
set -o errexit

echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Installing frontend dependencies & building React client..."
cd frontend-react
npm install
npm run build
cd ..

echo "Deployment build finished successfully!"
