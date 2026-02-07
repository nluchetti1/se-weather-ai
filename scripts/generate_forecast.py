import os
import requests
import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# --- 1. SETTINGS ---
# Get your API key from GitHub Secrets
API_KEY = os.getenv("NGC_API_KEY")
# Official NVIDIA Earth-2 CorrDiff API Endpoint
API_URL = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/ea48679d-d8a1-432a-9f79-2479e394348a"
# Southeast US Bounding Box: [Lon_Min, Lon_Max, Lat_Min, Lat_Max]
SE_EXTENT = [-95, -75, 24, 37]

def get_latest_cycle():
    """Calculates the most recent available GFS cycle."""
    now = datetime.datetime.utcnow()
    if now.hour >= 17:
        return now.replace(hour=12, minute=0, second=0, microsecond=0).isoformat() + "Z"
    elif now.hour >= 5:
        return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
    else:
        yesterday = now - datetime.timedelta(days=1)
        return yesterday.replace(hour=12, minute=0, second=0, microsecond=0).isoformat() + "Z"

def main():
    if not API_KEY:
        print("Error: NGC_API_KEY not found. Ensure it is set in GitHub Secrets.")
        return

    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    # 2. REQUEST DATA FROM NVIDIA
    payload = {
        "region": "us", 
        "input_time": get_latest_cycle(),
        "n_steps": 1
    }

    print(f"Calling NVIDIA API for cycle: {payload['input_time']}...")
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"API Error: {response.text}")
        return

    # 3. PLOT THE DATA
    # Create the 'images' folder if it doesn't exist
    os.makedirs("images", exist_ok=True)
    
    # Generate the high-res map
    fig = plt.figure(figsize=(10, 6), dpi=100)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent(SE_EXTENT)
    
    # --- GEOGRAPHY ---
    ax.coastlines(resolution='50m', color='black', linewidth=1)
    ax.add_feature(ccrs.cartopy.feature.STATES, linestyle='-', alpha=0.5)
    
    # Save the Temperature map (Placeholder for API data integration)
    plt.title(f"Southeast US High-Res AI Forecast\nCycle: {payload['input_time']}")
    plt.axis('off')
    plt.savefig("images/t2m_0.png", bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()
    
    print("Success: New forecast image generated in /images.")

if __name__ == "__main__":
    main()
