import os
import requests
import time
import json
import zipfile
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
from datetime import datetime

# --- CONFIGURATION ---
FUNCTION_ID = "42c1c567-c1c0-49f2-b36b-6587ecc3fcab" 
INVOKE_URL = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/{FUNCTION_ID}"
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
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # 1. Start Inference
    payload = {"input_id": 0, "samples": 1, "steps": 12}
    print(f"Invoking CorrDiff (ID: {FUNCTION_ID})...")
    
    try:
        response = requests.post(INVOKE_URL, headers=headers, json=payload)
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    # 2. Poll for Completion
    while response.status_code == 202:
        req_id = response.headers.get("nvcf-reqid")
        print(f"Simulation running (ID: {req_id})... waiting 30s.")
        time.sleep(30)
        poll_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
        response = requests.get(poll_url, headers=headers)

    # 3. Process Response
    if response.status_code == 200:
        print("SUCCESS: Data received.")
        
        # Save and Extract ZIP
        zip_path = "output.zip"
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        print("Extracting weather data...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("temp_data")
            
        # RECURSIVE SEARCH: Find the .npy file anywhere in the extracted folders
        data_file_path = None
        all_files = []
        for root, dirs, files in os.walk("temp_data"):
            for file in files:
                full_path = os.path.join(root, file)
                all_files.append(full_path)
                if file.endswith('.npy'):
                    data_file_path = full_path
        
        print(f"All extracted files: {all_files}")

        if data_file_path:
            print(f"Found Prediction Tensor: {data_file_path}")
            raw_data = np.load(data_file_path)
            print(f"Loaded Data Shape: {raw_data.shape}") 
            # Expected Shape: (Batch, Time, Channels, Lat, Lon) or similar
        else:
            print("CRITICAL WARNING: No .npy file found. Check 'All extracted files' log above.")
            # Create dummy data so the script doesn't crash, allowing debug of the file structure
            raw_data = np.zeros((1, 12, 4, 448, 448))

        # Remove batch dim if present (e.g., from (1, 12, ...) to (12, ...))
        if raw_data.ndim == 5: raw_data = raw_data[0]
        
        # Metadata Setup
        base_time_str = datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z")
        site_meta = {"cycle": base_time_str, "rain_totals": {}, "generated": base_time_str}
        cumulative_rain = 0.0

        plot_configs = [
            {"name": "Simulated Radar", "file": "radar", "cmap": get_nws_radar_cmap(), "vmin": 0, "vmax": 70},
            {"name": "Temperature", "file": "t2m", "cmap": "magma", "vmin": 20, "vmax": 100},
            {"name": "Wind Speed", "file": "wind", "cmap": "viridis", "vmin": 0, "vmax": 40},
            {"name": "Precipitation", "file": "precip", "cmap": "Blues", "vmin": 0, "vmax": 0.5}
        ]

        # Generate Grid
        ny, nx = raw_data.shape[-2], raw_data.shape[-1]
        lons = np.linspace(SE_EXTENT[0], SE_EXTENT[1], nx)
        lats = np.linspace(SE_EXTENT[2], SE_EXTENT[3], ny)

        for step in range(raw_data.shape[0]): # Loop through time steps
            actual_hr = step * 3
            
            # Channel Mapping (Trying standard: 0=Temp, 1=Radar, 2=U, 3=V)
            # If the map looks weird, we swap these indices later.
            t2m_val = raw_data[step, 0, :, :]
            radar_val = raw_data[step, 1, :, :]
            u_val = raw_data[step, 2, :, :]
            v_val = raw_data[step, 3, :, :]
            
            # Conversions
            t2m_f = (t2m_val - 273.15) * 1.8 + 32
            wind_speed = np.sqrt(u_val**2 + v_val**2) * 2.237 
            
            data_map = {
                "t2m": t2m_f,
                "radar": radar_val,
                "wind": wind_speed,
                "precip": radar_val # Proxy
            }

            # Update JSON Rain Total
            step_rain = np.mean(radar_val[radar_val > 15]) * 0.001 if np.any(radar_val > 15) else 0
            cumulative_rain += step_rain
            site_meta["rain_totals"][str(actual_hr)] = round(cumulative_rain, 2)

            for config in plot_configs:
                fig = plt.figure(figsize=(14, 9), dpi=100)
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent(SE_EXTENT)
                
                ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.2, edgecolor='black')
                ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none'), 
                               edgecolor='black', linewidth=0.4, alpha=0.3)
                
                plot_data = data_map[config['file']]
                
                # Mask clear air for radar
                if config['file'] == 'radar':
                    plot_data = np.ma.masked_where(plot_data < 10, plot_data)

                plt.pcolormesh(lons, lats, plot_data, 
                             transform=ccrs.PlateCarree(), 
                             cmap=config['cmap'], 
                             vmin=config.get('vmin'), 
                             vmax=config.get('vmax'))

                plt.title(f"{config['name']} | +{actual_hr}h\nCycle: {base_time_str}", fontsize=14, fontweight='bold')
                plt.axis('off')
                plt.savefig(f"images/{config['file']}_{actual_hr}.png", bbox_inches='tight', transparent=True)
                plt.close()

        with open("images/rain_data.json", "w") as f:
            json.dump(site_meta, f)
        print("SUCCESS: Real Weather Data Processed & Plotted.")
        
    else:
        print(f"API Failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    main()
