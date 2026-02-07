import os
import requests
import time
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# --- 1. CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 

# NEW BOUNDS: Focusing on NC, TN, and VA
# [Min Lon, Max Lon, Min Lat, Max Lat]
SE_EXTENT = [-89, -75, 33, 40] 

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    # Standard 3-hour steps for GFS blueprints
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    print(f"Initiating simulation for NC/TN/VA domain...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Processing (ID: {req_id})... waiting 30s.")
        time.sleep(30)
        response = requests.get(poll_url, headers=headers)

    if response.status_code == 200 and response.text:
        try:
            result = response.json()
            cycle_time = result.get("input_time", "Unknown")
            
            plot_configs = [
                {"name": "Simulated Radar", "file": "radar", "idx": 3},
                {"name": "Temperature", "file": "t2m", "idx": 0}
            ]

            for step in range(13):
                actual_hr = step * 3
                for config in plot_configs:
                    # Higher DPI for better zoomed-in detail
                    fig = plt.figure(figsize=(12, 9), dpi=120)
                    ax = plt.axes(projection=ccrs.PlateCarree())
                    ax.set_extent(SE_EXTENT)
                    
                    # Detailed Geography
                    ax.coastlines(resolution='10m', color='black', linewidth=1.2)
                    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.0)
                    counties = cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none')
                    ax.add_feature(counties, edgecolor='black', linewidth=0.4, alpha=0.4)
                    
                    plt.title(f"NC-TN-VA Regional {config['name']}\nCycle: {cycle_time} | Forecast: +{actual_hr}h", 
                              fontsize=14, fontweight='bold')
                    
                    plt.axis('off')
                    plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
                    plt.close()
            print("SUCCESS: Regional frames updated.")
        except Exception as e:
            print(f"Processing Error: {e}")
    else:
        print(f"API Error ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
