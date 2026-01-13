import requests
import os

key = "AIzaSyBp_ZT5ADJ3y5lUxePARLmoyF0N3-a3fUQ"

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"

try:
    resp = requests.get(url)
    if resp.status_code == 200:
        models = resp.json().get('models', [])
        print("Available Models:")
        for m in models:
            print(f"- {m['name']}")
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                 print(f"  (Supports generateContent)")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Failed: {e}")
