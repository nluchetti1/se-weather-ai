import os
import requests
import json

# --- CONFIGURATION ---
API_KEY = os.getenv("NGC_API_KEY") 

def main():
    if not API_KEY:
        print("CRITICAL: NGC_API_KEY is missing.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    
    print("Scanning your 271 authorized functions for Weather/Climate tools...")
    
    try:
        # Get the full list
        list_url = "https://api.nvcf.nvidia.com/v2/nvcf/functions"
        resp = requests.get(list_url, headers=headers)
        
        if resp.status_code != 200:
            print(f"Error fetching list: {resp.status_code}")
            return
            
        functions = resp.json().get('functions', [])
        
        # KEYWORDS TO SEARCH FOR
        keywords = ["corr", "diff", "earth", "climate", "weather", "fcn", "fourcast"]
        found_any = False

        print("\n=== MATCHING FUNCTIONS ===")
        for f in functions:
            name = f.get('name', '').lower()
            # Check if any keyword is in the function name
            if any(k in name for k in keywords):
                found_any = True
                print(f"Name:   {f.get('name')}")
                print(f"ID:     {f.get('id')}")
                print(f"Status: {f.get('status')}")
                print("-" * 40)

        if not found_any:
            print("No specific 'Earth-2' or 'CorrDiff' functions found in your list.")
            print("You likely have access to LLMs (Gemma, Llama) but not the Climate NIMs yet.")
        
    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    main()
