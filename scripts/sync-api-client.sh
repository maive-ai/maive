#!/bin/bash

# Script to sync API client with backend schemas
# This ensures the generated TypeScript client is always up to date

set -e  # Exit on any error

echo "🔄 Syncing API client with backend schemas..."

# Change to the project root
cd "$(dirname "$0")/.."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Are you in the project root?"
    exit 1
fi

# Step 1: Generate OpenAPI spec from FastAPI backend
echo "📝 Generating OpenAPI spec from FastAPI backend..."
cd apps/server
if ! uv run python scripts/generate_openapi.py; then
    echo "❌ Failed to generate OpenAPI spec"
    exit 1
fi
cd ../..

# Step 2: Clean the API client directory to ensure fresh generation
echo "🧹 Cleaning API client directory..."
cd packages/api
rm -rf client/
cd ../..

# Step 3: Generate TypeScript client from OpenAPI spec
echo "🔧 Generating TypeScript client from OpenAPI spec..."
cd packages/api
if ! pnpm generate:client; then
    echo "❌ Failed to generate TypeScript client"
    exit 1
fi
cd ../..

# Step 4: Typecheck affected packages to ensure everything is working
if ! pnpm --filter=@maive/web typecheck; then
    echo "❌ Web app typecheck failed after API sync"
    echo "💡 This might indicate that frontend code needs to be updated to match the new API types"
    exit 1
fi

echo "✅ API client sync completed successfully!"
echo "📦 The generated client is now up to date with your backend schemas." 