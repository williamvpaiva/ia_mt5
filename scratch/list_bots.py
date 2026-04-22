import httpx
import json

BASE_URL = "http://localhost:8000"

def list_bots():
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{BASE_URL}/bots/")
            if response.status_code == 200:
                bots = response.json()
                print(json.dumps(bots, indent=2))
            else:
                print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    list_bots()
