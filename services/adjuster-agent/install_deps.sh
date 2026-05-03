#!/bin/bash

# Simple dependency installation script for Adjuster Agent
# Installs dependencies in correct order to avoid conflicts

echo "📦 Installing Adjuster Agent dependencies..."
echo ""

# Install core dependencies first
echo "1️⃣ Installing core dependencies..."
pip install python-dotenv structlog psycopg2-binary confluent-kafka pgvector resend

# Install protobuf with specific version
echo ""
echo "2️⃣ Installing protobuf (3.20.x)..."
pip install "protobuf>=3.20.0,<4.0.0"

# Install PyTorch CPU version
echo ""
echo "3️⃣ Installing PyTorch (CPU version)..."
pip install "torch>=2.0.0,<2.3.0" --index-url https://download.pytorch.org/whl/cpu

# Install transformers
echo ""
echo "4️⃣ Installing transformers..."
pip install "transformers>=4.30.0,<4.40.0"

# Install sentence-transformers
echo ""
echo "5️⃣ Installing sentence-transformers..."
pip install "sentence-transformers>=2.2.0,<3.0.0"

# Install Chainlit
echo ""
echo "6️⃣ Installing Chainlit..."
pip install "chainlit>=1.0.0"

echo ""
echo "✅ All dependencies installed!"
echo ""
echo "🧪 Testing imports..."
python3 -c "
import sys
errors = []

try:
    import chainlit
    print('✅ chainlit')
except Exception as e:
    errors.append(f'chainlit: {e}')
    print(f'❌ chainlit: {e}')

try:
    import psycopg2
    print('✅ psycopg2')
except Exception as e:
    errors.append(f'psycopg2: {e}')
    print(f'❌ psycopg2: {e}')

try:
    from confluent_kafka import Consumer
    print('✅ confluent-kafka')
except Exception as e:
    errors.append(f'confluent-kafka: {e}')
    print(f'❌ confluent-kafka: {e}')

try:
    from sentence_transformers import SentenceTransformer
    print('✅ sentence-transformers')
except Exception as e:
    errors.append(f'sentence-transformers: {e}')
    print(f'❌ sentence-transformers: {e}')

try:
    import structlog
    print('✅ structlog')
except Exception as e:
    errors.append(f'structlog: {e}')
    print(f'❌ structlog: {e}')

if errors:
    print('')
    print('❌ Some imports failed. Please check the errors above.')
    sys.exit(1)
else:
    print('')
    print('🎉 All imports successful!')
    print('')
    print('You can now run:')
    print('  chainlit run app.py -w')
"

# Made with Bob
