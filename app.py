#!/usr/bin/env python3
"""
Alternative entry point for HeatSeeker Discord Bot with HTTP health check server.
This file is designed for Autoscale deployments that require HTTP endpoints.
"""

import os
import sys
import threading
from flask import Flask

# Import the main bot functionality
if __name__ == "__main__":
    # Add the current directory to path to import main
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import bot components from main.py
    from main import bot, run_flask
    
    # Start Flask server for health checks
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ HTTP health check server started on port", os.environ.get('PORT', 8080))
    
    # Get Discord token
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        print("Please set your Discord bot token in the .env file or environment variables")
        sys.exit(1)
    
    try:
        print("🚀 Starting HeatSeeker Discord Bot (HTTP-compatible mode)...")
        bot.run(token)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)