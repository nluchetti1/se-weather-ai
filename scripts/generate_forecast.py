import os
import json
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SE_EXTENT = [-89, -75, 33, 40] 

def get_nws_radar_cmap():
    return ListedColormap(["#00ECEC", "#01A0F6", "#0000F6", "#00FF00", "#00C800", 
                           "#009000", "#FFFF00", "#E7C000", "#FF9000", "#FF0000", 
                           "#D60000", "#AD0000", "#FF00FF", "#9955C9"])

def main():
    print("Running in DEMO MODE (Simulating AI Output)...")
    
    # 1. Setup metadata as if it came from the API
    base_time = datetime.utcnow()
    base_time_str = base_time.strftime("%Y-%m-%dT%H:00:00Z")
    
    site_meta = {
        "cycle": base_time_str,
        "rain_totals": {},
        "generated": base_time.strftime("%b %d, %Y %H:%M UTC")
    }
    cumulative_rain = 0.0

    plot_configs = [
        {"name": "Simulated Radar", "file": "radar", "cmap": get_nws_radar_cmap(), "unit": "dBZ"},
        {"name": "Temperature", "file": "t2m", "cmap": "magma", "unit": "°F"},
        {"name": "Precipitation", "file": "precip", "cmap": "Blues", "unit": "in"},
        {"name": "Wind Speed", "file": "wind", "cmap": "viridis", "unit": "MPH"}
    ]

    os.makedirs("images", exist_ok=True)

    # 2. Generate the 13 forecast steps
    for step in range(13):
        actual_hr = step * 3
        
        # Simulate realistic rain accumulation
        step_precip_in = 0.02 + (np.random.random() * 0.06) if step > 0 else 0
        cumulative_rain += step_precip_in
        site_meta["rain_totals"][str(actual_hr)] = round(cumulative_rain, 2)

        for config in plot_configs:
            fig = plt.figure(figsize=(14, 9), dpi=120)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(SE_EXTENT)
            
            # High-Res Geography
            ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.2, edgecolor='black')
            ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none'), 
                           edgecolor='black', linewidth=0.4, alpha=0.3)
            
            # --- SIMULATED DATA ---
            # Create a "fake" weather pattern moving across the map so you can test the animation
            # This ensures the map isn't blank
            lons = np.linspace(SE_EXTENT[0], SE_EXTENT[1], 100)
            lats = np.linspace(SE_EXTENT[2], SE_EXTENT[3], 100)
            lon_grid, lat_grid = np.meshgrid(lons, lats)
            
            # Create a moving "storm" blob based on the step
            blob_center_lon = -86 + (step * 0.5) 
            blob = np.exp(-((lon_grid - blob_center_lon)**2 + (lat_grid - 36)**2) / 1.5)
            data = blob * 60 if config['file'] == 'radar' else blob * 20 + 50 # random scaling
            
            # Plot the simulated data
            ax.pcolormesh(lons, lats, data, cmap=config['cmap'], transform=ccrs.PlateCarree(), alpha=0.6)

            plt.title(f"{config['name']} | +{actual_hr}h\nCycle: {base_time_str}", fontsize=14, fontweight='bold')
            plt.axis('off')
            plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
            plt.close()

    # 3. Save Metadata
    with open("images/rain_data.json", "w") as f:
        json.dump(site_meta, f)
    print(f"SUCCESS: Demo dashboard generated for cycle {base_time_str}")

if __name__ == "__main__":
    main()
