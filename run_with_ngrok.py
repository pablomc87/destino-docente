import subprocess
import time
from pyngrok import ngrok
import signal
import sys
import os

def signal_handler(signum, frame):
    print("\nShutting down...")
    ngrok.kill()
    if docker_process:
        docker_process.terminate()
    sys.exit(0)

def main():
    global docker_process
    docker_process = None
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start Docker container
    print("Starting Docker container...")
    docker_process = subprocess.Popen(
        ['docker', 'run', '-it', '--rm', '-p', '8000:8000', '-v', f'{os.getcwd()}:/app', '--name', 'schools-backend', 'schools-backend-dev'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for Docker to start
    time.sleep(5)
    
    # Start ngrok
    print("Starting ngrok...")
    public_url = ngrok.connect(8000).public_url
    print(f"\n🚀 Your application is now accessible at: {public_url}")
    print("Press Ctrl+C to stop the server")
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main() 