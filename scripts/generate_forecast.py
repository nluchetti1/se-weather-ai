import os
import requests
import time
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# --- CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-95, -75, 24, 37] 

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    # Requesting 36 steps for hourly output
    # Note: Ensure your NIM profile supports 1hr intervals
    payload = {"input_id": 0, "samples": 1, "steps": 36, "interval": 1}

    print("Initiating Hourly high-res simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Processing (ID: {req_id})... waiting 30s to avoid JSON errors.")
        time.sleep(30) # Increased delay to ensure data is ready
        response = requests.get(poll_url, headers=headers)

    if response.status_code == 200 and response.text:
        try:
            result = response.json()
            cycle_time = result.get("input_time", "Unknown")
            
            plot_configs = [
                {"name": "Simulated Radar", "file": "radar", "idx": 3},
                {"name": "Temperature", "file": "t2m", "idx": 0}
            ]

            # Loop through every hour for the first 24 hours
            for hr in range(0, 25):
                for config in plot_configs:
                    fig = plt.figure(figsize=(12, 8), dpi=100)
                    ax = plt.axes(projection=ccrs.PlateCarree())
                    ax.set_extent(SE_EXTENT)
                    
                    # High-Res Geography with Counties
                    ax.coastlines(resolution='10m', color='black', linewidth=1)
                    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.8)
                    counties = cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none')
                    ax.add_feature(counties, edgecolor='black', linewidth=0.2, alpha=0.3)
                    
                    plt.title(f"SE US {config['name']} | Cycle: {cycle_time}\nForecast: +{hr} Hour(s)", 
                              fontsize=14, fontweight='bold')
                    
                    plt.axis('off')
                    plt.savefig(f"images/{config['file']}_{hr}.png", bbox_inches='tight', transparent=True)
                    plt.close()
            print(f"SUCCESS: Generated 24 hourly frames for {len(plot_configs)} variables.")
        except Exception as e:
            print(f"JSON Error: {e} - Response may be empty.")
    else:
        print(f"API Error ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
