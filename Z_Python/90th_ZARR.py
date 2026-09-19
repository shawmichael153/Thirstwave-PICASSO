import os
import xarray as xr

# ==========================================================
# USER SETTINGS
# ==========================================================

AMOC_state = ['1251', '1281', '1301']

base_dir = "/data2/michsh/ET_os_calculated"

members = [f"{i:03d}" for i in range(1, 21)]

# CONUS bounds
s_lat = 24
n_lat = 52
w_lon = -125
e_lon = -67

# ==========================================================
# OPEN ALL HISTORICAL ETos FILES
# ==========================================================

for state in AMOC_state:

    output_file = (
        f"/data1/michsh/90th_zarr/HIST_{state}_ensemble_threshold.zarr"
    )
    
    initialization_periods = [f"{state}"]

    datasets = []

    for member in members:

        # Members 001-010 use BHISTcmip6
        if int(member) <= 10:
            perturbation = "BHISTcmip6"
        else:
            perturbation = "BHISTsmbb"

        member_dir = os.path.join(base_dir, state, member)

        cesm_member = f"LE2-{state}.{member}"

        filename = f"{perturbation}_{cesm_member}_ETos_daily.nc"
        filepath = os.path.join(member_dir, filename)

        if not os.path.exists(filepath):
            print(f"Missing: {filepath}")
            continue

        print(f"Opening {filename}")

        ds = xr.open_dataset(
            filepath,
            chunks={"time": 365}
        )

        # --------------------------------------------
        # Handle longitude convention
        # --------------------------------------------

        if ds.lon.max() > 180:
            actual_w_lon = w_lon + 360
            actual_e_lon = e_lon + 360
        else:
            actual_w_lon = w_lon
            actual_e_lon = e_lon

        # --------------------------------------------
        # Handle latitude orientation
        # --------------------------------------------

        if ds.lat[0] > ds.lat[-1]:
            lat_slice = slice(n_lat, s_lat)
        else:
            lat_slice = slice(s_lat, n_lat)

        # --------------------------------------------
        # Keep only CONUS ETos
        # --------------------------------------------

        etos = ds["ET_os"].sel(
            lat=lat_slice,
            lon=slice(actual_w_lon, actual_e_lon)
        )

        datasets.append(etos)

    print(f"\nLoaded {len(datasets)} datasets.")

    # ==========================================================
    # CREATE MEMBER DIMENSION
    # ==========================================================

    combined = xr.concat(
        datasets,
        dim="member"
    )

    combined = combined.chunk({
        "member": -1,   # put all members in one chunk
        "time": 214
    })

    print(combined)

    # Dimensions:
    # (member, time, lat, lon)

    # ==========================================================
    # COMPUTE ENSEMBLE 90TH PERCENTILE
    # ==========================================================

    threshold90 = (
        combined
        .groupby("time.dayofyear")
        .quantile(
            0.90,
            dim=("member", "time")
        )
    )

    print("Calculated ensemble 90th percentile.")

    # ==========================================================
    # APPLY 15-DAY SMOOTHING
    # ==========================================================

    threshold90 = (
        threshold90
        .rolling(
            dayofyear=15,
            center=True,
            min_periods=1
        )
        .mean()
    )

    print("Applied 15-day moving average.")

    # ==========================================================
    # SAVE
    # ==========================================================

    threshold90.to_dataset(name="threshold90").to_zarr(
        output_file,
        mode="w"
    )

    print(f"\nSaved ensemble threshold to:\n{output_file}")