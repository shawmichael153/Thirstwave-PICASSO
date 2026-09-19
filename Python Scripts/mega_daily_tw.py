import xarray as xr
from pathlib import Path

# Paths Setup
processed_dir = Path("/data1/michsh/daily_thirstwave")
output_dir = Path("/data1/michsh/combined_thirstwave")
output_dir.mkdir(parents=True, exist_ok=True)

time_periods = ['BHIST', 'BSSP370']
AMOC_states = ['1231', '1251', '1281', '1301']

def clean_extra_coordinates(ds):
    """
    Drops the lingering 'quantile' coordinate that causes 
    xr.open_mfdataset to crash during alignment.
    """
    return ds.drop_vars(['quantile'], errors='ignore')

for period in time_periods:
    print(f"--- Processing Group: {period} ---")
    
    amoc_datasets = []
    
    for state in AMOC_states:
        file_pattern = f"{period}_{state}_*.zarr"
        zarr_files = sorted([str(p) for p in processed_dir.glob(file_pattern)])
        
        if not zarr_files:
            print(f"Warning: No files found for {period} and State {state}. Skipping.")
            continue
            
        print(f"Combining 20 members for AMOC State: {state}...")
        
        # Open files and simply drop the conflicting 'quantile' coordinate
        ds_state = xr.open_mfdataset(
            zarr_files, 
            engine='zarr', 
            concat_dim='member', 
            combine='nested',
            preprocess=clean_extra_coordinates,  # <-- Just drops 'quantile' cleanly
            parallel=True
        )
        amoc_datasets.append(ds_state)
        
    if amoc_datasets:
        print(f"Combining all AMOC states for {period}...")
        combined_ds = xr.concat(amoc_datasets, dim='AMOC')
        
        # Optimize chunking layout for efficient loading later
        combined_ds = combined_ds.chunk({
            "AMOC": 1,
            "member": 1,
            "time": -1,
            "lat": 25,
            "lon": 25
        })
        
        for var in combined_ds.coords:
            combined_ds[var].encoding.clear()
        for var in combined_ds.data_vars:
            combined_ds[var].encoding.clear()
        combined_ds.encoding.clear()

        output_name = "HIST_tw_metrics.zarr" if period == 'BHIST' else "FTR_tw_metrics.zarr"
        output_path = output_dir / output_name
        
        print(f"Writing grand dataset to: {output_path}")
        combined_ds.to_zarr(output_path, mode="w")
        print(f"Successfully saved {output_name}!\n")
        
        combined_ds.close()