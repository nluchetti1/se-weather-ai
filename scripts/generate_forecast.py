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
            
        # Find the main data file (usually the largest .npy file)
        files = [f for f in os.listdir("temp_data") if f.endswith('.npy')]
        print(f"Found files: {files}")
        
        # Load the Prediction Tensor
        # CorrDiff output usually named like 'prediction.npy' or similar
        data_file = next((f for f in files if "pred" in f or "out" in f), files[0])
        raw_data = np.load(os.path.join("temp_data", data_file))
        print(f"Loaded Data Shape: {raw_data.shape}") 
        # Expected Shape: (Batch, Time, Channels, Lat, Lon) -> e.g. (1, 12, 4, 448, 448)

        # Remove batch dim if present
        if raw_data.ndim == 5: raw_data = raw_data[0]
        
        # Define Variable Indices (Standard CorrDiff US)
        # 0: Temperature (T2M)
        # 1: Maximum Radar Reflectivity (Refc)
        # 2: U-Wind (u10m)
        # 3: V-Wind (v10m)
        # Note: If these look wrong on the map, we swap them.
        
        # Metadata
        base_time_str = datetime.utcnow().strftime("%Y-%m-%dT%H:00:00Z")
        site_meta = {"cycle": base_time_str, "rain_totals": {}, "generated": base_time_str}
        cumulative_rain = 0.0

        plot_configs = [
            {"name": "Simulated Radar", "file": "radar", "cmap": get_nws_radar_cmap(), "vmin": 0, "vmax": 70},
            {"name": "Temperature", "file": "t2m", "cmap": "magma", "vmin": 20, "vmax": 100},
            {"name": "Wind Speed", "file": "wind", "cmap": "viridis", "vmin": 0, "vmax": 40},
            {"name": "Precipitation", "file": "precip", "cmap": "Blues", "vmin": 0, "vmax": 0.5}
        ]

        # Generate Lat/Lon Grid (Matching the array shape)
        # We construct a meshgrid to match the aspect ratio of the SE_EXTENT
        ny, nx = raw_data.shape[-2], raw_data.shape[-1]
        lons = np.linspace(SE_EXTENT[0], SE_EXTENT[1], nx)
        lats = np.linspace(SE_EXTENT[2], SE_EXTENT[3], ny)

        for step in range(raw_data.shape[0]): # Loop through time steps (0-11)
            actual_hr = step * 3
            
            # Extract variables for this step
            t2m_k = raw_data[step, 0, :, :]
            refc_dbz = raw_data[step, 1, :, :]
            u10 = raw_data[step, 2, :, :]
            v10 = raw_data[step, 3, :, :]
            
            # --- CONVERSIONS ---
            t2m_f = (t2m_k - 273.15) * 1.8 + 32
            wind_speed = np.sqrt(u10**2 + v10**2) * 2.237 # m/s to mph
            
            # Store Data for Plotting
            data_map = {
                "t2m": t2m_f,
                "radar": refc_dbz,
                "wind": wind_speed,
                "precip": refc_dbz # Using Refc as proxy for precip visual if channel missing
            }

            # Update Rain Total (Approximation from Radar dBZ)
            # If Z > 15, assume some rain. Very rough estimate for UI demo.
            step_rain = np.mean(refc_dbz[refc_dbz > 15]) * 0.001 if np.any(refc_dbz > 15) else 0
            cumulative_rain += step_rain
            site_meta["rain_totals"][str(actual_hr)] = round(cumulative_rain, 2)

            for config in plot_configs:
                fig = plt.figure(figsize=(14, 9), dpi=100)
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent(SE_EXTENT)
                
                ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=1.2, edgecolor='black')
                ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_2_counties', '10m', facecolor='none'), 
                               edgecolor='black', linewidth=0.4, alpha=0.3)
                
                # PLOT THE REAL DATA
                plot_data = data_map[config['file']]
                
                # Mask clear air for radar so map shows through
                if config['file'] == 'radar':
                    plot_data = np.ma.masked_where(plot_data < 10, plot_data)

                # pcolormesh needs coordinates to map array to map
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
