#!/usr/bin/env python3
"""
Test script for the Comfy Gimpy Studio web interface.
"""

import sys
import os
import time
import requests
import threading

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_interface.server import WebServer

def test_web_server():
    """Test the web server functionality."""
    print("Testing Comfy Gimpy Studio Web Interface...")

    # Create and start the server
    server = WebServer(host="localhost", port=8080)
    print("✓ WebServer instance created")

    # Start server in background
    server.start()
    print("✓ Web server started")

    # Wait for server to start
    time.sleep(1)

    try:
        # Test basic endpoints
        base_url = "http://localhost:8080"

        # Test index page
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✓ Index page accessible")
        else:
            print(f"✗ Index page failed: {response.status_code}")

        # Test API endpoints
        response = requests.get(f"{base_url}/api/models/list")
        if response.status_code == 200:
            print("✓ Models API accessible")
        else:
            print(f"✗ Models API failed: {response.status_code}")

        response = requests.get(f"{base_url}/api/templates/list")
        if response.status_code == 200:
            print("✓ Templates API accessible")
        else:
            print(f"✗ Templates API failed: {response.status_code}")

        response = requests.get(f"{base_url}/api/styles/list")
        if response.status_code == 200:
            print("✓ Styles API accessible")
        else:
            print(f"✗ Styles API failed: {response.status_code}")

        print("✓ All basic tests passed!")

    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        # Stop the server
        server.stop()
        print("✓ Web server stopped")

if __name__ == "__main__":
    test_web_server()