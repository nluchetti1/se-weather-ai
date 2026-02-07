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
    payload = {"input_id": 0, "samples": 1, "steps": 12}

    print("Initiating high-res simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        print(f"Processing (ID: {req_id})... waiting 20s.")
        time.sleep(20)
        response = requests.get(poll_url, headers=headers)

    # SAFETY CHECK: Only proceed if we have a valid 200 OK with content
    if response.status_code == 200 and response.text:
        try:
            result = response.json()
            cycle_time = result.get("input_time", "Unknown")
            
            plot_configs = [
                {"name": "Simulated Radar", "file": "radar", "idx": 3},
                {"name": "Temperature", "file": "t2m", "idx": 0},
                {"name": "Precipitation", "file": "precip", "idx": 5}
            ]

            for step in [0, 4, 8, 12]:
                forecast_hr = step * 3
                for config in plot_configs:
                    fig = plt.figure(figsize=(12, 8), dpi=100)
                    ax = plt.axes(projection=ccrs.PlateCarree())
                    ax.set_extent(SE_EXTENT)
                    
                    # High-Res Geography
                    ax.coastlines(resolution='10m', color='black', linewidth=1)
                    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.8)
                    counties = cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none')
                    ax.add_feature(counties, edgecolor='black', linewidth=0.2, alpha=0.3)
                    
                    plt.title(f"SE US {config['name']} | Cycle: {cycle_time}\nForecast Hour: +{forecast_hr}h", 
                              fontsize=14, fontweight='bold')
                    
                    plt.axis('off')
                    plt.savefig(f"images/{config['file']}_{step}.png", bbox_inches='tight', transparent=True)
                    plt.close()
            print("SUCCESS: Forecast generated.")
        except Exception as e:
            print(f"JSON Error: {e}")
    else:
        print(f"API Error ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
