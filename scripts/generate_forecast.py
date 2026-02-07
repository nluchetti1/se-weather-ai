import os
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime

# --- CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-95, -75, 24, 37] 

def main():
    if not API_KEY: return
    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    # Requesting 12 steps (representing a 36-hour forecast window)
    payload = {"input_id": 0, "samples": 1, "steps": 12}
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        time.sleep(15)
        response = requests.get(poll_url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        cycle_time = result.get("input_time", "Unknown")
        
        # Define variables and their specific tensor indices
        plot_configs = [
            {"name": "Simulated Radar", "file": "radar", "cmap": "magma", "idx": 3},
            {"name": "Temperature", "file": "t2m", "cmap": "magma", "idx": 0},
            {"name": "Precipitation", "file": "precip", "cmap": "Blues", "idx": 5}
        ]

        # Generate frames for every 4th step (0, 12, 24, 36 hours)
        for step in [0, 4, 8, 12]:
            forecast_hr = step * 3
            for config in plot_configs:
                fig = plt.figure(figsize=(12, 8), dpi=100)
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent(SE_EXTENT)
                
                # Geography: States + Granular Counties
                ax.coastlines(resolution='10m', color='black', linewidth=1)
                ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.8)
                counties = cfeature.NaturalEarthFeature(category='cultural', name='admin_2_counties', scale='10m', facecolor='none')
                ax.add_feature(counties, edgecolor='black', linewidth=0.2, alpha=0.3)
                
                # Dynamic Title
                plt.title(f"SE US {config['name']} | Cycle: {cycle_time}\nForecast Hour: +{forecast_hr}h", fontsize=14, fontweight='bold')

                plt.axis('off')
                plt.savefig(f"images/{config['file']}_{step}.png", bbox_inches='tight', transparent=True)
                plt.close()
    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    main()
