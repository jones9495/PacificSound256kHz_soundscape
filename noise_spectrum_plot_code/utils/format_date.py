from datetime import datetime
import httpx
from matplotlib import pyplot as plt
import numpy as np
from pydantic import BaseModel
import scipy
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors



class dateItem(BaseModel):
    start_date: datetime
    
def convert_to_date()->dateItem:

    count=0    
    while(True):
        count+=1
        try:
            date=input("Enter the starting date (format-DDMMYYYY) :")
            start_date = datetime.strptime(date, "%d%m%Y")
            return dateItem(start_date=start_date)
        
        except Exception as e:
            print (f"Invalid date format or something went wrong {e}")
            if count>5:
                exit()
            
    
# url of one of the file = https://github.com/jones9495/PacificSound256kHz_soundscape/blob/main
# PSD_2019/PSD_2019_01/calibrated_psd_20190101.mat
    
def url_maker(result:datetime)->str:
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/jones9495/PacificSound256kHz_soundscape/main/PSD_"
    start_day=result.day
    start_month=result.month
    start_year=result.year
    file_url=f"{GITHUB_BASE_URL}{start_year}/PSD_{start_year}_{start_month:02d}/calibrated_psd_{start_year}{start_month:02d}{start_day:02d}.mat"
    return file_url
    




def test_url():
    try:
        # Get the date item object
        date_item = convert_to_date()
        date=date_item.start_date
        filename=f"calibrated_psd_{date.year}{date.month:02d}{date.day:02d}.mat"
        # Pass the start_date from the `dateItem` model to `url_maker`
        date_formatted=f"{date.day:02d}/{date.month:02d}/{date.year}"
        res = url_maker(date_item.start_date)
        
        # Simulate retrieving data from the generated URL
        response=httpx.get(res)
            
        if response.status_code==200:
                with open(filename,"wb") as f:
                    f.write(response.content)
            
        else :
            print("Failed to download the file")
            
            print(f"Response: {response.status_code}")
            return
        
        load_data(filename=filename,date_formatted=date_formatted)
            
        # Return a JSON response for the client
        return {"file_url": res, "status_code": response.status_code, "data": response.text[:100]} 
        
    except Exception as e:
        return {"error": str(e)}
    
def load_data(filename:str,date_formatted:str):
    mat_data=scipy.io.loadmat(filename)
   
    psd_data = mat_data['calibrated_hourly_PSD_dB']  # Shape: (20000, 24)
    frequencies = mat_data['frequencies_Hz'].squeeze()  # Shape: (1, 20000)
    sample_rate = mat_data['sample_rate_Hz']  # Value: 48000
    spa_seconds = mat_data['spa_seconds']  # Value: 3600
   
    # plt.figure(figsize=(12,8))
    # cmap = cm.viridis
    # norm = mcolors.Normalize(vmin=0, vmax=23)
    
    # for hour in range(psd_data.shape[1]):

    #     if not np.all(np.isnan(psd_data[:, hour])):
    #         plt.plot(frequencies, psd_data[:, hour],linewidth=1.0,
    #             alpha=0.9)
          
    # plt.xscale('log') 
    # plt.title(f"Hourly Noise Spectrum – {date_formatted}")
    # plt.xlabel("Frequency (Hz)")
    # plt.ylabel("PSD (dB re 1 µPa²/Hz)")
    # plt.grid(True, which='both', linestyle='--', alpha=0.5)
    
    # sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    # sm.set_array(np.arrange(psd_data.shape[1]))
    # cbar = plt.colorbar(sm)
    # cbar.set_label("Hour of Day (0–23)")

    avg_psd = np.nanmean(psd_data, axis=1)
    plt.figure(figsize=(12, 8))
    plt.plot(frequencies, avg_psd, label="Average PSD")
    plt.xscale('log')
    plt.title(f"Average Noise Spectrum – {date_formatted}")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("PSD (dB re 1 µPa²/Hz)")
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.legend()
    plt.show()
    
    if os.path.exists(filename):
        os.remove(filename)
        print(f"Deleted the temporary saved file {filename}")
