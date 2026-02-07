import os
import requests
import time
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
# Switching to the more stable universal integration endpoint
INVOKE_URL = "https://integrate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-89, -75, 33, 40] 

def get_nws_radar_cmap():
    return ListedColormap(["#00ECEC", "#01A0F6", "#0000F6", "#00FF00", "#00C800", 
                           "#009000", "#FFFF00", "#E7C000", "#FF9000", "#FF0000", 
                           "#D60000", "#AD0000", "#FF00FF", "#9955C9"])

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    print("Initiating NC/TN/VA High-Res Simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    # --- 2. HARDENED POLLING ---
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        # Polling the universal status endpoint
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Simulation in progress... waiting 30s.")
        time.sleep(30)
        response = requests.get(poll_url, headers=headers)

    # Validate response before parsing
    if response.status_code == 200 and len(response.text.strip()) > 0:
        try:
            result = response.json()
            base_time_str = result.get("input_time", datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z"))
            base_time = datetime.strptime(base_time_str, "%Y-%m-%dT%H:%M:%SZ")

            plot_configs = [
                {"name": "Simulated Radar", "file": "radar", "idx": 3, "cmap": get_nws_radar_cmap(), "unit": "dBZ"},
                {"name": "Temperature", "file": "t2m", "idx": 0, "cmap": "magma", "unit": "°F"},
                {"name": "Precipitation", "file": "precip", "idx": 5, "cmap": "Blues", "unit": "in"},
                {"name": "Wind Speed", "file": "wind", "idx": 1, "cmap": "viridis", "unit": "MPH"}
            ]

            for step in range(13):
                actual_hr = step * 3
                valid_time = base_time + timedelta(hours=actual_hr)
                time_display = valid_time.strftime("%a %I %p")

                for config in plot_configs:
                    fig = plt.figure(figsize=(14, 9), dpi=120)
                    ax = plt.axes(projection=ccrs.PlateCarree())
                    ax.set_extent(SE_EXTENT)
                    
                    # Geography
                    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.2, edgecolor='black')
                    ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none'), 
                                   edgecolor='black', linewidth=0.4, alpha=0.3)
                    
                    sm = plt.cm.ScalarMappable(cmap=config['cmap'])
                    plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02, label=f"{config['name']} ({config['unit']})")

                    plt.title(f"{config['name']} | {time_display}\nForecast Hour: +{actual_hr}h", fontsize=14, fontweight='bold')
                    
                    plt.axis('off')
                    plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
                    plt.close()
            print("SUCCESS: 4-variable suite generated.")
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw Response: {response.text[:500]}") # Debugging dump
    else:
        print(f"API Error ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
