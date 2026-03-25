#!/bin/bash

# Verification script for Autonomous Agent Stack Dashboard

set -e

echo "🔍 Verifying Autonomous Agent Stack Dashboard..."
echo ""

ERRORS=0

# Check Node.js version
echo "📦 Checking Node.js version..."
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version must be 18 or higher. Current: $(node -v)"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Node.js version: $(node -v)"
fi

# Check if required files exist
echo ""
echo "📄 Checking required files..."

REQUIRED_FILES=(
    "package.json"
    "tsconfig.json"
    "next.config.js"
    "tailwind.config.ts"
    "app/layout.tsx"
    "app/page.tsx"
    "app/globals.css"
    "components/Navigation.tsx"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (missing)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check API endpoints
echo ""
echo "🔌 Checking API endpoints..."

API_ENDPOINTS=(
    "app/api/status/route.ts"
    "app/api/agents/route.ts"
    "app/api/tests/route.ts"
    "app/api/parity/route.ts"
    "app/api/commits/route.ts"
)

for endpoint in "${API_ENDPOINTS[@]}"; do
    if [ -f "$endpoint" ]; then
        echo "✅ $endpoint"
    else
        echo "❌ $endpoint (missing)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check pages
echo ""
echo "📄 Checking pages..."

PAGES=(
    "app/page.tsx"
    "app/tests/page.tsx"
    "app/parity/page.tsx"
    "app/agents/page.tsx"
)

for page in "${PAGES[@]}"; do
    if [ -f "$page" ]; then
        echo "✅ $page"
    else
        echo "❌ $page (missing)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check components
echo ""
echo "🧩 Checking components..."

COMPONENTS=(
    "components/Navigation.tsx"
    "components/StatCard.tsx"
    "components/AgentTable.tsx"
    "components/CommitList.tsx"
)

for component in "${COMPONENTS[@]}"; do
    if [ -f "$component" ]; then
        echo "✅ $component"
    else
        echo "❌ $component (missing)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check documentation
echo ""
echo "📚 Checking documentation..."

DOCS=(
    "README.md"
    "QUICKSTART.md"
    "DEVELOPMENT.md"
    "PROJECT.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "✅ $doc"
    else
        echo "❌ $doc (missing)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed! Dashboard is ready to use."
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Install dependencies: npm install"
    echo "   2. Start development server: npm run dev"
    echo "   3. Open http://localhost:3000"
    echo ""
    exit 0
else
    echo "❌ Found $ERRORS error(s). Please fix them before proceeding."
    echo ""
    exit 1
fi
