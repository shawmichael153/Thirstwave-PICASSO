import glob
import xarray as xr
import numpy as np
import os
import time
import requests

def download_single_netcdf(target_filepath):
    """
    Dynamically parses a filename to find its variable folder, 
    and downloads it directly from UCAR into its proper local path.
    """
    filename = os.path.basename(target_filepath)
    
    # Parse out the variable name (e.g., PS, TREFHTMX, WSPDSRFAV)
    try:
        parts = filename.split('.')
        variable_name = parts[8]
    except IndexError:
        print(f"--> [ERROR] Could not parse variable from filename: {filename}")
        return False

    # Build the exact UCAR URL path including the variable subfolder
    download_UCAR_base = 'https://osdf-director.osg-htc.org/ncar/gdex/d651056/CESM2-LE/atm/proc/tseries/day_1'
    clean_url = f"{download_UCAR_base}/{variable_name}/{filename}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    MAX_RETRIES = 5
    attempt = 0
    success = False
    
    os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
    
    print(f"--> [RECOVERY] Downloading from: {clean_url}")
    
    while attempt < MAX_RETRIES and not success:
        try:
            with requests.get(clean_url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status() 
                
                with open(target_filepath, "wb") as f:
                    f.write(r.content)
            success = True
            print(f"--> [SUCCESS] Replaced corrupted file: {filename}")
            return True
            
        except (requests.exceptions.RequestException, ConnectionResetError) as e:
            attempt += 1
            print(f"--> [WARNING] Download attempt {attempt}/{MAX_RETRIES} failed. Error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(5)
            else:
                print(f"--> [CRITICAL] Could not recover {filename} after max retries.")
                if os.path.exists(target_filepath):
                    os.remove(target_filepath)
                return False

def sat_vp(t_air):
    e_s = 0.6108 * np.exp((17.27 * t_air) / (t_air + 237.3))
    return e_s

def calculation_of_ET_os(ds):
    #-------------------------------------------- Finding Delta (kPA / C) ----------------------------------------------
    T_max = ds['TREFHTMX'] - 273.15
    T_min = ds['TREFHTMN'] - 273.15

    T = (T_max + T_min) / 2
    delta = (2503 * np.exp((17.27 * T) / (T + 237.3))) / ((T + 237.3) ** 2)

    #------------------------------------------- Finding Net Raditation (MJ / m^2 / d) ---------------------------------

    # CESM2 defults net radiation for shortwave and longwave to W/m^2. One Watt is 1J/s. There are 86,400s in a day. 
    # Convert this to Joules then Megajoules: 86,499 / 1000000 = 0.0864
    R_ns = ds['FSNS'] * 0.0864   # Net Shortwave converted to MJ/m^2/d  
    R_nl = ds['FLNS'] * 0.0864   # Net Longwave converted to MJ/m^2/d
    R_n = R_ns - R_nl 

    #------------------------------------------- Soil Heat Flux (MJ / m^2 / d) -----------------------------------------
    G = 0   # Heat flux cancels out during a 24 hour period

    # ------------------------------------------ Psychrometric Constant (kPa / C) --------------------------------------
    P = ds['PS'] / 1000  # Need surface pressure to calc y + divide by 1000 to get from Pa to kPa
    y = 0.000665 * P    # As stated in literature

    # ------------------------------------------ Numerator Constant (K / mm / s^3 / Mg / d) ----------------------------
    C_n = 900   # Value for short crop ET

    # ------------------------------------------ Mean Daily Wind Speed at 2m height (m / s) ----------------------------
    u_2 = ds['WSPDSRFAV']   # m/s from raw NetCDF data

    # ------------------------------------------ Denominator Constant (s / m)-------------------------------------------
    C_d = 0.34  # Value for short crop ET

    # ------------------------------------------ Saturation and Actual Vapor Pressure (kPa) ----------------------------
    q = ds['QREFHT']  # Already in kg/kg, no conversion needed
    e_a = (P * q) / (0.622 + (0.378 * q))   # Rearranged form of equation for specific humidity

    es_tmin = sat_vp(T_min)     # Assuming the max e_s is found at the lowest temp of the day
    es_tmax = sat_vp(T_max)     # Assuming the min e_s is found at the highest temp of the day
    e_s = (es_tmin + es_tmax) / 2   # Mean e_s

    # ----- The Equation -----
    ET_os = (0.408 * delta * (R_n - G) + y * (C_n / (T + 273)) * u_2 * (e_s - e_a)) / (delta + y * (1 + C_d * u_2))

    # Converting the final DataArray to a Dataset keeps it lazy and fast.
    ds_etos = ET_os.to_dataset(name='ET_os')
    ds_etos['ET_os'].attrs['units'] = 'mm/day'
    ds_etos['ET_os'].attrs['long_name'] = 'Short Crop Refrence Evapotranspiration'

    return ds_etos

# Execution starts here
members = [f"{i:03d}" for i in range(1, 21)]

AMOC_state = '1301'
perturbations = ['BHISTcmip6', 'BHISTsmbb', 'BSSP370cmip6', 'BSSP370smbb']

print("Starting batch processing...")

for member in members:

    data_dir = f"/data2/michsh/full_member_data/{AMOC_state}/{member}"
    output_dir = f"/data2/michsh/ET_os_calculated/{AMOC_state}/{member}"
    os.makedirs(output_dir, exist_ok=True)

    for state in perturbations:
        
        cesm_member = f"LE2-{AMOC_state}.{member}"
        output_filename = os.path.join(
            output_dir,
            f"{state}_{cesm_member}_ETos_daily.nc"
        )

        if os.path.exists(output_filename):
            print(f"\n========== File already exists, skipping: {output_filename} ==========\n")
            continue

        file_pattern = (
            f"b.e21.{state}.f09_g17.{cesm_member}.cam.h1.*.nc"
        )
        full_path_pattern = os.path.join(data_dir, file_pattern)

        success = False
        max_retries = 3
        retry_count = 0

        while not success and retry_count < max_retries:
            matching_files = sorted(glob.glob(full_path_pattern))
            if not matching_files:
                break

            try:
                ds = xr.open_mfdataset(
                    matching_files,
                    combine='by_coords',
                    engine='netcdf4',
                    data_vars='all',
                    chunks={'time': 365}
                )
                success = True
                print(f"Opened {len(matching_files)} files")

            except OSError as e:
                retry_count += 1
                error_msg = str(e)
                print(f"\n[ERROR] Caught NetCDF HDF error during open: {error_msg}")

                if "'" in error_msg:
                    corrupted_file = error_msg.split("'")[1]

                    if os.path.exists(corrupted_file):
                        print(f"--> Deleting corrupted file: {corrupted_file}")
                        os.remove(corrupted_file)

                        download_success = download_single_netcdf(corrupted_file)
                        if not download_success:
                            print("--> [ABORT] Download recovery failed. Moving on.")
                            break
                    else:
                        print(f"--> Indicated path does not exist on disk: {corrupted_file}")
                        break
                else:
                    print("--> Error string unparsable. Aborting loop.")
                    break

        if not success:
            print(f"[SKIP] Skipping processing for {output_filename}\n")
            continue

        ds = ds.sel(time=ds.time.dt.month.isin(range(4, 11)))
        ds_etos = calculation_of_ET_os(ds)

        print(f"Writing metrics to: {output_filename}")
        ds_etos.to_netcdf(output_filename)

        ds_etos.close()
        ds.close()

        print(f"[SUCCESS] Completed {cesm_member}\n")

print("\nAll tasks completed successfully!")