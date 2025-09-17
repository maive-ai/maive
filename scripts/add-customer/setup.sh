#!/bin/bash

# Setup script for Interactive Customer Creator
# Makes the Python script executable and installs dependencies

set -e

echo "🏠 Setting up Interactive Customer Creator..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make Python script executable
chmod +x "$SCRIPT_DIR/add_customer.py"
echo "✅ Made add_customer.py executable"

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "❌ pip is not installed. Please install Python and pip first."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  python scripts/add-customer/add_customer.py --stack-name your-stack-name"
echo ""
echo "Or if you have python3 specifically:"
echo "  python3 scripts/add-customer/add_customer.py --stack-name your-stack-name"
