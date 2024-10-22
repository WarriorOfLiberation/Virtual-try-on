# run.py
from waitress import serve
from app import app
import os
from dotenv import load_dotenv

load_dotenv()

def start_server():
    print("Starting server...")
    print("Your application is running on port 8000")
    print("Ngrok is forwarding requests from your configured URL")
    print("Press Ctrl+C to stop the server")
    
    # Run waitress server
    serve(app, host='127.0.0.1', port=8080, threads=6)

if __name__ == '__main__':
    start_server()