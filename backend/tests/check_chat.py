import requests
import json
import time

def check_chat():
    url = "http://localhost:8000/api/v1/chat"
    payload = {
        "message": "Thông tin về Lộc Trời?"
    }
    
    # Wait for server
    print("Waiting for server...")
    time.sleep(5)
    
    try:
        print(f"Sending request to {url}")
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Response:")
            print(data.get('response'))
            print("\nSources:")
            for s in data.get('sources', []):
                print(s)
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    check_chat()
