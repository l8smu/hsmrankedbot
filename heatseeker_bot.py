#!/usr/bin/env python3
"""
HeatSeeker Discord Bot - Legacy entry point for backward compatibility.
This file redirects to the main application with HTTP health check support.
"""

import os
import sys

# Redirect to main application
if __name__ == "__main__":
    # Add the current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import and run the main application with HTTP support
    from app import *
    
    print("🔄 HeatSeeker Bot starting through legacy entry point...")
    print("⚠️  Consider updating to use 'python app.py' or 'python main.py' directly")