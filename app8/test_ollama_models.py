#!/usr/bin/env python3
"""Test different Ollama models to see which one works"""

import requests
import json

def test_model(model_name):
    """Test a specific model"""
    print(f"\n🧪 Testing model: {model_name}")
    
    try:
        # Test with simple chat API
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                "stream": False
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("message", {}).get("content", "No content")
            print(f"✅ SUCCESS: {content[:100]}...")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Cannot connect to Ollama")
        return False
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timed out")
        return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_all_models():
    """Test all available models"""
    models_to_test = [
        "llama3.2:latest",  # Smaller, should be faster
        "llama3:latest",    #  current model
        "llama3.1:latest",  # Alternative
        "mymodel:latest"    # Custom model
    ]
    
    print("=== TESTING OLLAMA MODELS ===")
    
    working_models = []
    
    for model in models_to_test:
        if test_model(model):
            working_models.append(model)
    
    print(f"\n📊 RESULTS:")
    print(f"Working models: {working_models}")
    print(f"Failed models: {[m for m in models_to_test if m not in working_models]}")
    
    if working_models:
        print(f"\n💡 RECOMMENDATION: Use '{working_models[0]}' in your app")
    else:
        print("\n❌ No models are working. Check Ollama server.")

if __name__ == "__main__":
    test_all_models()