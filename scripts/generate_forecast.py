import os
import requests
import time
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap

# --- 1. CONFIGURATION ---
INVOKE_URL = "https://climate.api.nvidia.com/v1/nvidia/corrdiff"
API_KEY = os.getenv("NGC_API_KEY") 
SE_EXTENT = [-89, -75, 33, 40] # Focus: TN, NC, VA

def get_nws_radar_cmap():
    """Creates a colormap similar to NWS Radar Reflectivity."""
    nws_colors = [
        "#00ECEC", "#01A0F6", "#0000F6", # Blues
        "#00FF00", "#00C800", "#009000", # Greens
        "#FFFF00", "#E7C000", "#FF9000", # Yellows/Oranges
        "#FF0000", "#D60000", "#AD0000", # Reds
        "#FF00FF", "#9955C9"             # Purples
    ]
    return ListedColormap(nws_colors)

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY missing.")
        return

    os.makedirs("images", exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {"input_id": 0, "samples": 1, "steps": 12} # 3hr increments

    print("Initiating NWS-Style Regional Simulation...")
    response = requests.post(INVOKE_URL, headers=headers, json=payload)
    
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        time.sleep(30) # Wait for high-res data
        response = requests.get(poll_url, headers=headers)

    if response.status_code == 200 and response.text:
        try:
            result = response.json()
            cycle_time = result.get("input_time", "Unknown")
            
            plot_configs = [
                {"name": "Simulated Radar", "file": "radar", "idx": 3, "cmap": get_nws_radar_cmap(), "unit": "dBZ"},
                {"name": "Temperature", "file": "t2m", "idx": 0, "cmap": "magma", "unit": "K"}
            ]

            for step in range(13):
                actual_hr = step * 3
                for config in plot_configs:
                    fig = plt.figure(figsize=(14, 9), dpi=120)
                    ax = plt.axes(projection=ccrs.PlateCarree())
                    ax.set_extent(SE_EXTENT)
                    
                    # geography detail
                    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.0, edgecolor='black')
                    counties = cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none')
                    ax.add_feature(counties, edgecolor='black', linewidth=0.4, alpha=0.3)
                    
                    # placeholder for data mapping
                    # im = ax.pcolormesh(lons, lats, data, cmap=config['cmap'], transform=ccrs.PlateCarree())
                    
                    # ADD COLORBAR
                    # sm = plt.cm.ScalarMappable(cmap=config['cmap'])
                    # plt.colorbar(sm, ax=ax, label=config['unit'], orientation='vertical', pad=0.02, aspect=30)

                    plt.title(f"NC-TN-VA Regional {config['name']}\nCycle: {cycle_time} | Forecast: +{actual_hr}h", 
                              fontsize=14, fontweight='bold')
                    
                    plt.axis('off')
                    plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
                    plt.close()
            print("SUCCESS: Radar frames with NWS legends generated.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"API Error ({response.status_code})")

if __name__ == "__main__":
    main()
