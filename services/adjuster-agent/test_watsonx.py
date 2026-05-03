#!/usr/bin/env python3
"""Test script for Watsonx.ai LLM integration."""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_watsonx_import():
    """Test if watsonx.ai SDK can be imported."""
    print("🧪 Testing Watsonx.ai SDK import...")
    try:
        from ibm_watsonx_ai.foundation_models import Model
        from ibm_watsonx_ai import Credentials
        print("✅ Watsonx.ai SDK imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Watsonx.ai SDK: {e}")
        return False

def test_credentials():
    """Test if credentials are configured."""
    print("\n🔑 Testing credentials configuration...")
    
    required_vars = [
        "WATSONX_API_KEY",
        "WATSONX_PROJECT_ID",
        "WATSONX_URL"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"❌ Missing: {var}")
        else:
            # Mask sensitive values
            if "KEY" in var or "PASSWORD" in var:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    if missing:
        print(f"\n❌ Missing credentials: {', '.join(missing)}")
        return False
    
    print("✅ All credentials configured!")
    return True

def test_watsonx_client():
    """Test if WatsonxClient can be initialized."""
    print("\n🤖 Testing WatsonxClient initialization...")
    try:
        from watsonx_client import get_watsonx_client
        
        client = get_watsonx_client()
        print("✅ WatsonxClient initialized successfully!")
        print(f"   Model: {client.model_id}")
        print(f"   URL: {client.url}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize WatsonxClient: {e}")
        return False

def test_simple_generation():
    """Test simple text generation."""
    print("\n💬 Testing simple text generation...")
    try:
        from watsonx_client import get_watsonx_client
        
        client = get_watsonx_client()
        
        prompt = "What is an insurance claim?"
        print(f"   Prompt: {prompt}")
        
        response = client.generate_response(prompt)
        print(f"   Response: {response[:100]}...")
        
        if response and len(response) > 10:
            print("✅ Text generation successful!")
            return True
        else:
            print("❌ Generated response is too short or empty")
            return False
            
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False

def test_intent_extraction():
    """Test intent extraction."""
    print("\n🎯 Testing intent extraction...")
    try:
        from watsonx_client import get_watsonx_client
        
        client = get_watsonx_client()
        
        message = "Show me details for claim #123"
        print(f"   Message: {message}")
        
        intent_data = client.extract_intent(message)
        print(f"   Intent: {intent_data.get('intent')}")
        print(f"   Entities: {intent_data.get('entities')}")
        
        if intent_data and intent_data.get('intent'):
            print("✅ Intent extraction successful!")
            return True
        else:
            print("❌ Intent extraction returned empty result")
            return False
            
    except Exception as e:
        print(f"❌ Intent extraction failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Watsonx.ai LLM Integration Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Import
    results.append(("SDK Import", test_watsonx_import()))
    
    # Test 2: Credentials
    results.append(("Credentials", test_credentials()))
    
    # Test 3: Client initialization
    if results[-1][1]:  # Only if credentials are OK
        results.append(("Client Init", test_watsonx_client()))
    
    # Test 4: Simple generation
    if results[-1][1]:  # Only if client init is OK
        results.append(("Text Generation", test_simple_generation()))
    
    # Test 5: Intent extraction
    if results[-1][1]:  # Only if generation is OK
        results.append(("Intent Extraction", test_intent_extraction()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Watsonx.ai LLM is ready!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
