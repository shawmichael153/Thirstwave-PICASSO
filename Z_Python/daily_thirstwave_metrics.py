import cftime
import pandas as pd
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
from scipy.ndimage import label
from pathlib import Path

def detect_events(mask):

    n = len(mask)

    thirstwave = np.zeros(n, dtype=bool)
    event_id = np.zeros(n, dtype=np.int32)

    start = None
    current_event = 1

    for i, above in enumerate(mask): # i is counting the days, above is the boolean value

        if above and start is None:
            start = i

        elif not above and start is not None:

            duration = i - start

            if duration >= 3:
                thirstwave[start:i] = True
                event_id[start:i] = current_event
                current_event += 1

            start = None

    # Handle event ending on final day
    if start is not None:

        duration = n - start

        if duration >= 3:
            thirstwave[start:] = True
            event_id[start:] = current_event

    return thirstwave, event_id

def daily_thirstwave(time_period, state, member, baseline):

    # Make sure the file naming convention is correct
    if time_period == 'BHIST':
        if int(member) <= 10:
            bmb = f'{time_period}cmip6'
        else:
            bmb = f'{time_period}smbb' 

    if time_period == 'BSSP370':
        if int(member) <= 10:
            bmb = f'{time_period}cmip6'
        else:
            bmb = f'{time_period}smbb' 

    file_name = f'{bmb}_LE2-{state}.{member}_ETos_daily.nc'

    file_path = Path(f'{input_data_path}/{state}/{member}/{file_name}')

    # Verify the file exists before trying to open it
    if file_path.exists():
        print(f"Opening: {file_name}")

        # Open the file
        ds = xr.open_dataset(file_path)

    else:
        print(f"Warning: File not found -> {file_name}")

    # Define the CONUS bounds 
    s_lat = 24
    n_lat = 52
    w_lon = -125
    e_lon = -67

    # West lon coordinate adjustments for both CONUS and upper midwest bounds 
    if ds['lon'].max() > 180 and w_lon < 0:
        actual_w_lon = w_lon + 360  
    else:
        actual_w_lon = w_lon

    # East lon coordinate adjustments for both CONUS and upper midwest bounds 
    if ds['lon'].max() > 180 and e_lon < 0:
        actual_e_lon = e_lon + 360  
    else:
        actual_e_lon = e_lon

    # Determines which way the coords are dispayed in the array and aligns them properly
    if ds['lat'].values[0] > ds['lat'].values[-1]:
        lat_slice = slice(n_lat, s_lat)  
    else:
        lat_slice = slice(s_lat, n_lat) 

    print(actual_e_lon, actual_w_lon, lat_slice)

    etos = ds['ET_os'].sel(lat=lat_slice, lon=slice(actual_w_lon, actual_e_lon))
    threshold = baseline['threshold90'].sel(lat=lat_slice, lon=slice(actual_w_lon, actual_e_lon))

    etos = etos.assign_coords(dayofyear=etos.time.dt.dayofyear)

    daily_threshold = threshold.sel(dayofyear=etos.dayofyear)

    excess = etos - daily_threshold

    exceedance = excess > 0

    exceedance = exceedance.chunk({
        "time": -1,
        "lat": 25,
        "lon": 25,
    })

    etos = etos.chunk({
        "time": -1,
        "lat": 25,
        "lon": 25,
        })

    daily_threshold = daily_threshold.chunk({
        "time": -1,
        "lat": 25,
        "lon": 25,
        })

    print(etos.chunks)
    print(exceedance.chunks)

    thirstwave, event_id = xr.apply_ufunc(
        detect_events,
        exceedance,
        input_core_dims=[["time"]],
        output_core_dims=[["time"], ["time"]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[bool, np.int32],
    )

    # Intensity above the moving threshold only during thirstwaves
    tw_intensity = excess.where(thirstwave)

    # Actual ETos values only during thirstwaves
    actual_tw_ET_os = etos.where(thirstwave)

    daily_etos = xr.Dataset(
        coords={
            "time": etos.time,
            "lat": etos.lat,
            "lon": etos.lon,},
        data_vars={
            "ET_os": etos.astype(np.float32),

            "tw_intensity": tw_intensity.astype(np.float32),

            "actual_tw_ET_os": actual_tw_ET_os.astype(np.float32),

            "event_id": event_id.astype(np.int32),},)

    daily_etos = daily_etos.expand_dims(
    AMOC=[state],
    member=[member])

    output = (
    f"/data1/michsh/daily_thirstwave/"
    f"{time_period}_{state}_{member}.zarr")

    encoding = {
        "ET_os": {
            "dtype": "float32",
            "compressor": None,
        },
        "tw_intensity": {
            "dtype": "float32",
            "compressor": None,
        },
        "actual_tw_ET_os": {
            "dtype": "float32",
            "compressor": None,
        },
        "event_id": {
            "dtype": "int32",
            "compressor": None,},}

    daily_etos.to_zarr(
        output,
        mode="w",
        encoding=encoding,)

    ds.close()
    print(f'Closed data for {file_name}\n')

# ==============================================================================

time_periods = ['BHIST', 'BSSP370']

# Open the baseline file 
baseline = xr.open_zarr("/data1/michsh/90th_zarr/HIST_BASELINE.zarr")

input_data_path = '/data2/michsh/ET_os_calculated'

# Define desired AMOC state and member
AMOC_state = ['1231', '1251', '1281', '1301']
members = [f"{i:03d}" for i in range(1, 21)]

for time_period in time_periods:
    for state in AMOC_state:
        for member in members:
            daily_thirstwave(time_period = time_period, 
                             state=state, 
                             member=member,
                             baseline=baseline)

baseline.close()