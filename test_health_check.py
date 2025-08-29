#!/usr/bin/env python3
"""
Test script to verify health check endpoints are working
"""

import requests
import time
import threading
import os
from main import run_flask

def test_health_endpoints():
    """Test the health check endpoints"""
    print("🧪 Testing health check endpoints...")
    
    # Start Flask server in background for testing
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    port = int(os.environ.get('PORT', 8080))
    base_url = f"http://localhost:{port}"
    
    try:
        # Test root endpoint
        print(f"Testing {base_url}/")
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Root endpoint working!")
            print(f"   Status: {data.get('status')}")
            print(f"   Service: {data.get('service')}")
            print(f"   Bot Ready: {data.get('bot_ready')}")
        else:
            print(f"❌ Root endpoint failed with status {response.status_code}")
            return False
        
        # Test health endpoint
        print(f"Testing {base_url}/health")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working!")
        else:
            print(f"❌ Health endpoint failed with status {response.status_code}")
            return False
        
        print("\n✅ Health check endpoints working correctly!")
        print("🚢 Bot is ready for Autoscale deployment!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing endpoints: {e}")
        print("🔧 Make sure the Flask server is running")
        return False

if __name__ == "__main__":
    test_health_endpoints()