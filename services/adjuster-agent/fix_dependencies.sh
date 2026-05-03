#!/bin/bash

# Fix Dependencies Script for Adjuster Agent
# This script resolves protobuf compatibility issues with Python 3.12

echo "🔧 Fixing dependencies for Adjuster Agent..."
echo ""

# Uninstall conflicting packages
echo "📦 Uninstalling conflicting packages..."
pip uninstall -y protobuf tensorflow transformers sentence-transformers torch 2>/dev/null

# Install compatible protobuf first
echo "📦 Installing compatible protobuf..."
pip install "protobuf>=3.20.0,<4.0.0"

# Install PyTorch (CPU version for faster install)
echo "📦 Installing PyTorch..."
pip install "torch>=2.0.0,<2.3.0" --index-url https://download.pytorch.org/whl/cpu

# Install transformers with compatible version
echo "📦 Installing transformers..."
pip install "transformers>=4.30.0,<4.40.0"

# Install sentence-transformers
echo "📦 Installing sentence-transformers..."
pip install "sentence-transformers>=2.2.0,<3.0.0"

# Install remaining dependencies
echo "📦 Installing remaining dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Dependencies fixed!"
echo ""
echo "🧪 Testing imports..."
python3 -c "
import sys
try:
    from sentence_transformers import SentenceTransformer
    print('✅ sentence-transformers: OK')
except Exception as e:
    print(f'❌ sentence-transformers: {e}')
    sys.exit(1)

try:
    import psycopg2
    print('✅ psycopg2: OK')
except Exception as e:
    print(f'❌ psycopg2: {e}')
    sys.exit(1)

try:
    from confluent_kafka import Consumer
    print('✅ confluent-kafka: OK')
except Exception as e:
    print(f'❌ confluent-kafka: {e}')
    sys.exit(1)

try:
    import chainlit
    print('✅ chainlit: OK')
except Exception as e:
    print(f'❌ chainlit: {e}')
    sys.exit(1)

print('')
print('🎉 All imports successful!')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete! You can now run:"
    echo "   python3 test_setup.py"
    echo "   ./start.sh"
else
    echo ""
    echo "❌ Some imports failed. Please check the error messages above."
    exit 1
fi

# Made with Bob
