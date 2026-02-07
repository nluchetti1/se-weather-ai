import os
import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
# The URL must point to YOUR running Docker container
# If running on the same machine, use localhost. 
# If on a remote VM, use that VM's IP address.
INVOKE_URL = "http://localhost:8000/v1/infer" 
SE_EXTENT = [-89, -75, 33, 40] 

def get_nws_radar_cmap():
    return ListedColormap(["#00ECEC", "#01A0F6", "#0000F6", "#00FF00", "#00C800", 
                           "#009000", "#FFFF00", "#E7C000", "#FF9000", "#FF0000", 
                           "#D60000", "#AD0000", "#FF00FF", "#9955C9"])

def main():
    # Note: For local inference, you typically pass the input as a file or huge tensor.
    # This script assumes the NIM is running and ready to accept the specific CorrDiff payload.
    # Check the "Deployment Guide" for the exact 'input_array' format required.
    
    print(f"Connecting to Local NIM at {INVOKE_URL}...")
    
    # Payload for local inference often requires a file upload or specific JSON structure
    # This is a placeholder for the standard /infer call
    try:
        # Health check first
        health = requests.get("http://localhost:8000/v1/health/ready")
        if health.status_code != 200:
            print("Error: CorrDiff NIM is not running. Please run the 'docker run' command first.")
            return
            
        # Example Payload (Consult docs for 'input_array' generation)
        # requests.post(INVOKE_URL, ...)
        
        # --- MOCKING SUCCESS FOR DASHBOARD TESTING ---
        # Since we can't run a 26GB model in this script execution, we generate the 
        # dashboard assets using the same logic as before so you can test your HTML.
        print("NIM connection confirmed (Simulated). Generating assets...")
        
        base_time_str = datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z")
        site_meta = {
            "cycle": base_time_str,
            "rain_totals": {},
            "generated": datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")
        }
        cumulative_rain = 0.0

        plot_configs = [
            {"name": "Simulated Radar", "file": "radar", "idx": 3, "cmap": get_nws_radar_cmap(), "unit": "dBZ"},
            {"name": "Temperature", "file": "t2m", "idx": 0, "cmap": "magma", "unit": "°F"},
            {"name": "Precipitation", "file": "precip", "idx": 5, "cmap": "Blues", "unit": "in"},
            {"name": "Wind Speed", "file": "wind", "idx": 1, "cmap": "viridis", "unit": "MPH"}
        ]

        os.makedirs("images", exist_ok=True)
        for step in range(13):
            actual_hr = step * 3
            step_precip_in = 0.03 + (np.random.random() * 0.05) if step > 0 else 0
            cumulative_rain += step_precip_in
            site_meta["rain_totals"][str(actual_hr)] = round(cumulative_rain, 2)

            for config in plot_configs:
                fig = plt.figure(figsize=(14, 9), dpi=120)
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent(SE_EXTENT)
                ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.2, edgecolor='black')
                ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none'), 
                               edgecolor='black', linewidth=0.4, alpha=0.3)
                
                plt.title(f"{config['name']} | +{actual_hr}h\nCycle: {base_time_str}", fontsize=14, fontweight='bold')
                plt.axis('off')
                plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
                plt.close()

        with open("images/rain_data.json", "w") as f:
            json.dump(site_meta, f)
        print("SUCCESS: Local dashboard assets updated.")

    except requests.exceptions.ConnectionError:
        print("CRITICAL ERROR: Could not connect to localhost:8000.")
        print("You MUST run the NVIDIA CorrDiff Docker container before running this script.")

if __name__ == "__main__":
    main()
