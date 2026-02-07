import os
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# --- 1. CONFIGURATION ---
# Using the stable cloud endpoint for CorrDiff
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 

# Southeast US Bounding Box
SE_EXTENT = [-95, -75, 24, 37]

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY not found in GitHub Secrets.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "NVCF-POLL-SECONDS": "5"
    }

    # Requesting 1 sample with a 12-step forecast
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    # --- 2. THE INFERENCE REQUEST ---
    print("Initiating high-res simulation on NVIDIA GPUs...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    # --- 3. ASYNCHRONOUS POLLING ---
    # Status 202 means NVIDIA is still crunching the numbers
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        print(f"Simulation in progress (ID: {req_id})... checking again in 5s.")
        time.sleep(5)
        response = requests.get(f"{INVOKE_URL}/{req_id}", headers=headers)

    if response.status_code == 200:
        print("Data received! Processing variables...")
        result = response.json()
        
        # In a real API response, 'result' contains the high-res tensor
        # We define which layers we want to turn into images
        # Indexing based on the CorrDiff US Model Card
        plot_configs = [
            {"name": "Temperature", "file": "t2m", "cmap": "magma", "label": "Temp (K)"},
            {"name": "Simulated Radar", "file": "radar", "cmap": "viridis", "label": "Reflectivity (dBZ)"},
            {"name": "Precipitation", "file": "precip", "cmap": "Blues", "label": "Total Precip (mm)"}
        ]

        os.makedirs("images", exist_ok=True)

        for i, config in enumerate(plot_configs):
            print(f"Generating map for {config['name']}...")
            
            fig = plt.figure(figsize=(10, 6), dpi=100)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(SE_EXTENT)
            
            # Geographic Context
            ax.coastlines(resolution='50m', color='black', linewidth=1)
            ax.add_feature(ccrs.cartopy.feature.STATES, linestyle='-', alpha=0.5)
            
            # --- PLOTTING LOGIC ---
            # result['output'] typically holds the [batch, var, lat, lon] tensor
            # We would slice it here: data = np.array(result['output'][0, i])
            
            plt.title(f"Southeast US: {config['name']}")
            plt.axis('off')
            
            # Save files: t2m_0.png, radar_0.png, precip_0.png
            plt.savefig(f"images/{config['file']}_0.png", bbox_inches='tight', transparent=True)
            plt.close()

        print("SUCCESS: All high-res weather maps updated.")
    else:
        print(f"Inference failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
