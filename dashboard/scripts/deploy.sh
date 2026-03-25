#!/bin/bash

# Deployment script for Autonomous Agent Stack Dashboard

set -e

echo "🚀 Deploying Autonomous Agent Stack Dashboard..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version must be 18 or higher. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the project
echo "🔨 Building the project..."
npm run build

# Check if build was successful
if [ -d ".next" ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed!"
    exit 1
fi

# Deploy to Vercel (if Vercel CLI is installed)
if command -n vercel &> /dev/null; then
    echo "🚀 Deploying to Vercel..."
    vercel --prod
    echo "✅ Deployment to Vercel complete!"
else
    echo "ℹ️  Vercel CLI not found. Skipping Vercel deployment."
    echo "   To deploy to Vercel, install the CLI: npm i -g vercel"
    echo "   Then run: vercel --prod"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📱 Next steps:"
echo "   1. Open the dashboard in your browser"
echo "   2. Take screenshots and save them to public/screenshots/"
echo "   3. Share the dashboard URL in Telegram"
echo ""
echo "🎉 Happy monitoring!"
