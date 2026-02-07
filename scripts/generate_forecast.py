import os
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# --- 1. CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-95, -75, 24, 37]

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    # --- 2. INITIAL REQUEST ---
    print("Initiating simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    # --- 3. CORRECT POLLING LOGIC ---
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        # Polling the specific NVCF status endpoint to avoid 404s
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Processing (ID: {req_id})... waiting 15s.")
        time.sleep(15)
        response = requests.get(poll_url, headers=headers)

    if response.status_code == 200:
        print("Success! Plotting variables...")
        # Indexing based on standard CorrDiff US output channels
        plot_configs = [
            {"name": "Simulated Radar", "file": "radar", "cmap": "magma"},
            {"name": "Temperature", "file": "t2m", "cmap": "magma"},
            {"name": "Precipitation", "file": "precip", "cmap": "Blues"}
        ]

        for config in plot_configs:
            fig = plt.figure(figsize=(10, 6), dpi=100)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(SE_EXTENT)
            ax.coastlines(resolution='50m', color='white', linewidth=1)
            ax.add_feature(ccrs.cartopy.feature.STATES, linestyle=':', alpha=0.5)
            
            plt.title(f"SE US: {config['name']}")
            plt.axis('off')
            plt.savefig(f"images/{config['file']}_0.png", bbox_inches='tight', transparent=True)
            plt.close()
    else:
        print(f"Failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
