#!/bin/bash

# Claims Processor Service - Quick Start Script

set -e

echo "=================================="
echo "Claims Processor Service"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  WARNING: .env file not found!"
    echo "Please create .env from .env.example and configure your credentials:"
    echo "  cp .env.example .env"
    echo "  nano .env  # or use your preferred editor"
    echo ""
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo ""
echo "Configuration:"
echo "  Kafka Bootstrap: $KAFKA_BOOTSTRAP_SERVERS"
echo "  Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo "  Input Topic: $KAFKA_TOPIC_INGEST"
echo ""

# Ask user what to do
echo "What would you like to do?"
echo "  1) Setup Kafka topics"
echo "  2) Run test producer (send sample claims)"
echo "  3) Start claims processor service"
echo "  4) All of the above (setup → test → run)"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "Setting up Kafka topics..."
        python setup_topics.py
        ;;
    2)
        echo ""
        echo "Running test producer..."
        python test_producer.py
        ;;
    3)
        echo ""
        echo "Starting claims processor service..."
        echo "Press Ctrl+C to stop"
        echo ""
        python main.py
        ;;
    4)
        echo ""
        echo "Step 1: Setting up Kafka topics..."
        python setup_topics.py
        
        echo ""
        echo "Step 2: Running test producer..."
        python test_producer.py
        
        echo ""
        echo "Step 3: Starting claims processor service..."
        echo "Press Ctrl+C to stop"
        echo ""
        sleep 2
        python main.py
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Made with Bob
