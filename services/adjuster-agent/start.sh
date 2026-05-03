#!/bin/bash

# Startup script for Adjuster Agent Chainlit Interface

echo "🚀 Starting Adjuster Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check database connection
echo "🔍 Checking database connection..."
python3 -c "
import psycopg2
from config import Config
config = Config()
try:
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode=config.DB_SSLMODE,
        connect_timeout=5
    )
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Please check your database configuration in .env"
    exit 1
fi

# Start Chainlit
echo "🎯 Launching Chainlit interface..."
echo "📱 Access the interface at: http://localhost:8000"
echo ""
chainlit run app.py -w

# Made with Bob
