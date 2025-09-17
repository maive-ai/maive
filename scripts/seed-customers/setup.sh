#!/bin/bash

# Setup script for customer seeding
echo "🚀 Setting up customer seeding script..."

# Create virtual environment if it doesn't exist
if [ ! -d "scripts/seed-customers/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv scripts/seed-customers/venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source scripts/seed-customers/venv/bin/activate

# Install requirements
echo "📚 Installing requirements..."
pip install -r scripts/seed-customers/requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To run the seeder:"
echo "  source scripts/seed-customers/venv/bin/activate"
echo "  python scripts/seed-customers/seed_customers.py --stack-name your-stack-name --dry-run"
echo ""
echo "Remove --dry-run to actually seed the data."
