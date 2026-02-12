import os
import requests
import time
import json
import zipfile
import shutil
import random
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
FUNCTION_ID = "42c1c567-c1c0-49f2-b36b-6587ecc3fcab" 
INVOKE_URL = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/{FUNCTION_ID}"
API_KEY = os.getenv("NGC_API_KEY") 

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # RETRY LOOP: Try input_id 0, then 1 if 500 error occurs
    for attempt_id in [0, 1]:
        print(f"\n--- Attempting Inference with Input ID {attempt_id} ---")
        payload = {"input_id": attempt_id, "samples": 1, "steps": 12}
        
        try:
            response = requests.post(INVOKE_URL, headers=headers, json=payload)
            
            # Poll if accepted
            while response.status_code == 202:
                req_id = response.headers.get("nvcf-reqid")
                print(f"Simulation Running (ID: {req_id})... waiting 30s.")
                time.sleep(30)
                poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
                response = requests.get(poll_url, headers=headers)
            
            if response.status_code == 200:
                print("SUCCESS: Connection Established.")
                break # Exit retry loop
            else:
                print(f"Request Failed ({response.status_code}): {response.text}")
                if response.status_code != 500:
                    return # Don't retry client errors (400s), only server errors (500s)
                time.sleep(5) # Cooldown before retry

        except Exception as e:
            print(f"Connection Error: {e}")
            return

    # PROCESS SUCCESSFUL RESPONSE
    if response.status_code == 200:
        # Save ZIP
        zip_path = "output.zip"
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        # Extract to temp folder
        extract_dir = "temp_data"
        if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
        os.makedirs(extract_dir)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        print(f"Extracted contents: {os.listdir(extract_dir)}")

        # --- UNIVERSAL FILE HANDLER ---
        # 1. Check for PNGs (Pre-rendered images)
        # 2. Check for NPY (Raw Data)
        
        found_pngs = [f for f in os.listdir(extract_dir) if f.endswith('.png')]
        
        if found_pngs:
            print(f"Found Pre-Rendered Images: {found_pngs}")
            # Map NVIDIA names to Our names
            # Expected: output0_t2m.png, output0_tp.png (precip), output0_w10m.png (wind)
            
            var_map = {
                "t2m": "t2m",       # Temperature
                "wind": "w10m",     # Wind
                "precip": "tp",     # Total Precip
                "radar": "cat"      # Simulated Radar often labeled 'cat' or derived from Precip
            }
            
            for my_var, nvidia_tag in var_map.items():
                # Find the file that matches the tag
                match = next((f for f in found_pngs if nvidia_tag in f), None)
                
                # Fallback: Use Precip for Radar if Radar missing
                if not match and my_var == 'radar':
                    match = next((f for f in found_pngs if 'tp' in f), None)

                if match:
                    src = os.path.join(extract_dir, match)
                    print(f"Processing {my_var} from {match}...")
                    
                    # COPY TO ALL TIME STEPS
                    # Since we only get 1 frame (output0), we copy it to all 12 hours
                    # so the website slider works without crashing.
                    for step in range(13):
                        dst = f"images/{my_var}_{step*3}.png"
                        shutil.copy(src, dst)
        else:
            print("WARNING: No PNGs found. Checking for .npy...")
            # (Add NPY handling here if needed, but logs confirm PNGs are sent)

        # Generate Metadata
        base_time_str = datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z")
        site_meta = {
            "cycle": base_time_str,
            "rain_totals": {str(i*3): "0.15" for i in range(13)}, # Mock data for UI
            "generated": datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")
        }
        
        with open("images/rain_data.json", "w") as f:
            json.dump(site_meta, f)
            
        print("SUCCESS: Dashboard assets updated.")

if __name__ == "__main__":
    main()
