import requests
import sys

BASE_URL = "http://localhost:8001"

def main():
    try:
        r = requests.get(f"{BASE_URL}/projects")
        r.raise_for_status()
        projects = r.json()
        if not projects:
            print("No projects found")
            return
        pid = projects[0]['id']
        print(f"Project: {pid}")
        r2 = requests.post(f"{BASE_URL}/projects/{pid}/export-video")
        print("Status:", r2.status_code)
        print("Response:", r2.json())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
