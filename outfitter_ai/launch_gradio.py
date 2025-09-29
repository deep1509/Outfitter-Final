#!/usr/bin/env python3
"""
Simple launcher for Outfitter.ai Gradio interface
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gradio_app import create_complete_interface

def main():
    print("🚀 Starting Outfitter.ai Gradio Interface...")
    print("📍 Interface will be available at: http://localhost:7860")
    print("🔗 For external access, set share=True in gradio_app.py")
    print("-" * 60)
    
    interface = create_complete_interface()
    interface.launch(
        server_name="127.0.0.1",  # Local only for security
        server_port=7860,
        share=False,  # Set to True for public tunnel
        show_error=True,
        debug=False
    )

if __name__ == "__main__":
    main()