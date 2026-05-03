#!/bin/bash

echo "==================================="
echo "Starting E-Commerce Backend Server"
echo "==================================="
echo ""

# Check if database exists
if [ ! -f "marketplace.db" ]; then
    echo "⚠️  Database not found. Creating database with sample data..."
    python3 seed_data.py
    echo ""
fi

echo "🚀 Starting backend server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API Docs will be available at: http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn app.main:app --reload
