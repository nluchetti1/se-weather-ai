import os
import requests
import time
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-89, -75, 33, 40] # TN, NC, VA Focus

def get_nws_radar_cmap():
    """NWS standard reflectivity colors."""
    nws_colors = ["#00ECEC", "#01A0F6", "#0000F6", "#00FF00", "#00C800", 
                  "#009000", "#FFFF00", "#E7C000", "#FF9000", "#FF0000", 
                  "#D60000", "#AD0000", "#FF00FF", "#9955C9"]
    return ListedColormap(nws_colors)

def main():
    if not API_KEY: return
    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    print("Initiating Regional Simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    # --- 2. HARDENED POLLING ---
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Simulation in progress... waiting 30s.")
        time.sleep(30)
        response = requests.get(poll_url, headers=headers)

    # Validate response content before JSON parsing
    if response.status_code == 200 and len(response.text) > 0:
        try:
            result = response.json()
            # Parse the cycle time to calculate local valid times
            base_time_str = result.get("input_time", "2026-02-07T12:00:00Z")
            base_time = datetime.strptime(base_time_str, "%Y-%m-%dT%H:%M:%SZ")

            plot_configs = [
                {"name": "Simulated Radar", "file": "radar", "idx": 3, "cmap": get_nws_radar_cmap()},
                {"name": "Temperature", "file": "t2m", "idx": 0, "cmap": "magma"}
            ]

            for step in range(13):
                actual_hr = step * 3
                valid_time = base_time + timedelta(hours=actual_hr)
                time_display = valid_time.strftime("%A %I %p") # e.g. Saturday 04 PM

                for config in plot_configs:
                    fig = plt.figure(figsize=(14, 9), dpi=120)
                    ax = plt.axes(projection=ccrs.PlateCarree())
                    ax.set_extent(SE_EXTENT)
                    
                    # geography
                    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.2, edgecolor='black')
                    counties = cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none')
                    ax.add_feature(counties, edgecolor='black', linewidth=0.4, alpha=0.3)
                    
                    # Add NWS Colorbar
                    sm = plt.cm.ScalarMappable(cmap=config['cmap'])
                    plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02, label=config['name'])

                    plt.title(f"{config['name']} | Valid: {time_display}\n(Cycle: {base_time_str})", 
                              fontsize=14, fontweight='bold')
                    
                    plt.axis('off')
                    plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
                    plt.close()
            print("SUCCESS: Localized frames generated.")
        except Exception as e:
            print(f"Error processing JSON: {e}")
    else:
        print(f"API Error ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
