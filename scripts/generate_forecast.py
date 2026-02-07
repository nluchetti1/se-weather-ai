import os
import requests
import json
import time
from datetime import datetime

# --- CONFIGURATION ---
# We start with the standard US CorrDiff ID. If this fails, the script goes into discovery mode.
TARGET_FUNCTION_ID = "62758169-122e-4b68-b769-e33b666d9f8c" 
INVOKE_URL = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/{TARGET_FUNCTION_ID}"
API_KEY = os.getenv("NGC_API_KEY") 

def main():
    if not API_KEY:
        print("CRITICAL: NGC_API_KEY is missing from environment variables.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # 1. Try the Standard Request
    print(f"Attempting to invoke Function ID: {TARGET_FUNCTION_ID}...")
    payload = {"input_id": 0, "samples": 1, "steps": 12}
    
    try:
        response = requests.post(INVOKE_URL, headers=headers, json=payload)
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    # 2. Handle 404 / 403 by Listing Available Functions
    if response.status_code in [404, 403]:
        print(f"\n!!! ERROR {response.status_code}: Target Function Not Found or Forbidden. !!!")
        print("Starting Discovery Mode to find valid Function IDs for your key...")
        
        # Query the Functions List Endpoint
        list_url = "https://api.nvcf.nvidia.com/v2/nvcf/functions"
        list_resp = requests.get(list_url, headers=headers)
        
        if list_resp.status_code == 200:
            functions = list_resp.json().get('functions', [])
            print(f"\nSUCCESS: Found {len(functions)} authorized functions for this API Key:")
            print("="*60)
            if not functions:
                print(" - [NONE] Your API Key has no authorized Cloud Functions.")
                print("   Action: Go to build.nvidia.com and generate a new key.")
            for f in functions:
                # Print Name, ID, and Status
                name = f.get('name', 'Unknown')
                fid = f.get('id', 'No ID')
                status = f.get('status', 'Unknown')
                print(f"Name: {name}")
                print(f"ID:   {fid}")
                print(f"Status: {status}")
                print("-" * 60)
        else:
            print(f"Discovery Failed ({list_resp.status_code}): {list_resp.text}")
            
    # 3. Handle Success (200/202)
    elif response.status_code == 202:
        print("Success! The default Function ID is valid.")
        req_id = response.headers.get("nvcf-reqid")
        print(f"Request ID: {req_id} (Simulation Started)")
        # (We stop here for this test run just to confirm access)
        
    else:
        print(f"Unexpected API Error ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
