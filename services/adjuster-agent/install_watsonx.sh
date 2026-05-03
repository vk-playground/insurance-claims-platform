#!/bin/bash
# Install IBM Watsonx.ai SDK for LLM capabilities

set -e

echo "🤖 Installing IBM Watsonx.ai SDK..."

# Install watsonx.ai package
pip3 install ibm-watsonx-ai>=0.2.0

echo "✅ Watsonx.ai SDK installed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Ensure your .env file has watsonx credentials:"
echo "   WATSONX_API_KEY=your_api_key"
echo "   WATSONX_PROJECT_ID=your_project_id"
echo "   WATSONX_URL=https://ca-tor.ml.cloud.ibm.com"
echo "   WATSONX_MODEL_ID=ibm/granite-13b-chat-v2"
echo ""
echo "2. Test the installation:"
echo "   python3 -c 'from ibm_watsonx_ai.foundation_models import Model; print(\"✅ Watsonx.ai SDK ready!\")'"
echo ""
echo "3. Start the Adjuster Agent:"
echo "   chainlit run app.py"

# Made with Bob
