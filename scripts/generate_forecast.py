import os
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime

# --- 1. CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-95, -75, 24, 37] # [Min Lon, Max Lon, Min Lat, Max Lat]

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    # We request a 12-step forecast (36 hours if 3hr intervals)
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    print("Initiating high-res simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Processing (ID: {req_id})... waiting 15s.")
        time.sleep(15)
        response = requests.get(poll_url, headers=headers)

    if response.status_code == 200:
        print("Success! Unpacking AI Data...")
        result = response.json()
        
        # Get metadata for the title
        cycle_time = result.get("input_time", "Unknown Cycle")
        
        # Variables configuration
        plot_configs = [
            {"name": "Simulated Radar", "file": "radar", "cmap": "magma", "idx": 3},
            {"name": "Temperature", "file": "t2m", "cmap": "magma", "idx": 0},
            {"name": "Precipitation", "file": "precip", "cmap": "Blues", "idx": 5}
        ]

        # Iterate through forecast steps (we'll save step 0, 4, 8, 12)
        for step in [0, 4, 8, 12]:
            for config in plot_configs:
                fig = plt.figure(figsize=(12, 8), dpi=100)
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent(SE_EXTENT)
                
                # --- GEOGRAPHY & COUNTIES ---
                ax.coastlines(resolution='10m', color='black', linewidth=1)
                ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.8)
                # Add US Counties for high-res detail
                counties = cfeature.NaturalEarthFeature(
                    category='cultural', name='admin_2_counties',
                    scale='10m', facecolor='none'
                )
                ax.add_feature(counties, edgecolor='gray', linewidth=0.3, alpha=0.5)
                
                # --- TITLE WITH CYCLE & FORECAST HOUR ---
                forecast_hour = step * 3 # Assuming 3-hour model steps
                plt.title(f"SE US: {config['name']}\nCycle: {cycle_time} | Forecast: +{forecast_hour}hr", 
                          fontsize=14, fontweight='bold', pad=10)

                # --- DATA MAPPING ---
                # In actual deployment, we extract the array from result['output']
                # result['output'] structure: [samples, steps, variables, lat, lon]
                # data = np.array(result['output'][0, step, config['idx']])
                # plt.pcolormesh(lons, lats, data, transform=ccrs.PlateCarree(), cmap=config['cmap'])

                plt.axis('off')
                filename = f"images/{config['file']}_{step}.png"
                plt.savefig(filename, bbox_inches='tight', transparent=True)
                plt.close()
                print(f"Saved: {filename}")
    else:
        print(f"Failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
