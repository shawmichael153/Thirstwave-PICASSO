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
import pyarrow as pa
from collections import Counter

def extract_events(event_ids, intensity, times): 
    """
    Extracts individual event metrics including annual and monthly frequencies.
    Only events with a duration >= 3 days are included.
    """ 
    records = [] 
    years = np.unique([t.year for t in times]) 

    for year in years: 
        # Create a mask matching the current year 
        year_mask = np.array([t.year == year for t in times]) 
        yearly_ids = event_ids[year_mask] 
        yearly_intensity = intensity[year_mask] 
        yearly_times = times[year_mask] 
        
        raw_events = np.unique(yearly_ids[yearly_ids > 0]) 
        
        # --- FILTER FOR EVENTS WITH DURATION >= 3 DAYS ---
        valid_events = []
        for event in raw_events:
            event_duration = np.sum(yearly_ids == event)
            if event_duration >= 3:
                valid_events.append(event)
        
        # Annual frequency based ONLY on valid events (duration >= 3)
        annual_frequency = len(valid_events) 
        
        if annual_frequency == 0: 
            continue 
        
        event_start_months = {}

        # Determine the starting month of each valid event
        for event in valid_events:
            mask = yearly_ids == event
            first_idx = np.where(mask)[0][0]
            event_start_months[event] = yearly_times[first_idx].month

        # Count how many valid events start in each month
        monthly_counts = Counter(event_start_months.values())

        # Create one record per valid event
        for event in valid_events:
            mask = yearly_ids == event
            idx = np.where(mask)[0]

            start_time = str(yearly_times[idx[0]])
            end_time = str(yearly_times[idx[-1]])
            start_month = event_start_months[event]

            records.append(
                {
                    "year": int(year),
                    "month": int(start_month),
                    "annual_frequency": annual_frequency,
                    "monthly_frequency": monthly_counts[start_month],
                    "event_id": int(event),
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": len(idx),
                    "mean_intensity": float(yearly_intensity[mask].mean()),
                    "max_intensity": float(yearly_intensity[mask].max()),
                    "total_intensity": float(yearly_intensity[mask].sum()),
                }
            )
    
    return pd.DataFrame(records)

datasets = {
    "HIST": "/data1/michsh/combined_thirstwave/HIST_tw_metrics.zarr",
    "FUT": "/data1/michsh/combined_thirstwave/FTR_tw_metrics.zarr",
}

column_order = [
    "period",
    "AMOC",
    "member",
    "lat",
    "lon",
    "year",
    "month",
    "annual_frequency",
    "monthly_frequency",
    "event_id",
    "start_time",
    "end_time",
    "duration",
    "mean_intensity",
    "max_intensity",
    "total_intensity",
]

for period, zarr_path in datasets.items():

    print("\n==============================")
    print(f"Processing {period} dataset")
    print("==============================")

    ds = xr.open_zarr(zarr_path)

    output_file = f"/data1/michsh/CSV/{period}_derived_metrics_2.csv"

    # Remove previous file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)

    first_write = True
    total_events = 0

    for target_amoc in ds.AMOC.values:
        for target_member in ds.member.values:

            print(f"{period} | AMOC {target_amoc} | Member {target_member}")

            ds_subset = ds.sel(
                AMOC=target_amoc,
                member=target_member
            )

            time_values = ds_subset.time.values

            for i, lat in enumerate(ds_subset.lat.values):
                for j, lon in enumerate(ds_subset.lon.values):

                    cell_ds = ds_subset.isel(lat=i, lon=j)

                    cell_event_ids = cell_ds.event_id.values
                    cell_intensity = cell_ds.tw_intensity.values

                    # Skip cells with no thirstwave events
                    if not np.any(cell_event_ids > 0):
                        continue

                    events_df = extract_events(
                        cell_event_ids,
                        cell_intensity,
                        time_values,
                    )

                    if events_df.empty:
                        continue

                    events_df["period"] = period
                    events_df["AMOC"] = target_amoc
                    events_df["member"] = target_member
                    events_df["lat"] = lat
                    events_df["lon"] = lon

                    events_df = events_df[column_order]

                    total_events += len(events_df)

                    events_df.to_csv(
                        output_file,
                        mode="a",
                        header=first_write,
                        index=False,
                    )

                    first_write = False

    print("\n-------------------------------------")
    print(f"{period} COMPLETE")
    print(f"Total events written: {total_events:,}")
    print(f"Saved to: {output_file}")
    print("-------------------------------------")