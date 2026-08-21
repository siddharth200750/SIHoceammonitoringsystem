import subprocess
import time
import webbrowser
import os
import sys

def main():
    print(" Starting Ocean Monitoring System...")

    # 1. Run the initial data fetch once
    print(" [1/3] Fetching latest ocean alerts...")
    subprocess.run([sys.executable, "monitor.py"])

    # 2. Launch the Flask API server as a background process
    print(" [2/3] Starting backend API server (api.py)...")
    api_process = subprocess.Popen([sys.executable, "api.py"])

    # Wait 2 seconds for Flask to initialize
    time.sleep(2)

    # 3. Open the frontend HTML map in your default browser
    print(" [3/3] Launching Live Map...")
    html_path = os.path.abspath("index.html")
    webbrowser.open(f"file://{html_path}")

    print("\n System running! Press Ctrl+C in this terminal to stop.")
    try:
        # Keep runner alive while the API runs
        api_process.wait()
    except KeyboardInterrupt:
        print("\n Shutting down API server...")
        api_process.terminate()

if __name__ == "__main__":
    main()