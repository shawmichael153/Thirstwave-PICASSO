import os
import sys
import time
import requests
import numpy as np

def download_cesm_members(target_amoc, target_members, file_list_path, base_download_destination):
    """
    Downloads CESM2-LE files for a specified list of ensemble members.
    
    Parameters:
    - target_amoc (str): The AMOC state (e.g., "1251", "1231")
    - target_members (list of int): List of integer members (e.g., [1, 2, 3, 10])
    - file_list_path (str): Path to the local text file containing all downloadable files
    - base_download_destination (str): The parent folder where data should be stored
    """
    
    # 1. Verify master file list exists
    if not os.path.exists(file_list_path):
        print(f"Error: The file {file_list_path} does not exist. Run your generator script first.")
        return

    # Read the master list once into memory to save I/O time during loops
    with open(file_list_path, 'r') as f:
        master_file_lines = [line.strip() for line in f if line.strip()]

    # Global Download Settings
    download_UCAR_path = 'https://osdf-director.osg-htc.org/ncar/gdex/d651056/CESM2-LE/atm/proc/tseries/day_1'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    MAX_RETRIES = 3

    # 2. Loop through each member provided in the list
    for member in target_members:
        # Format member to 3 digits (e.g., 1 -> "001", 12 -> "012")
        member_str = f"{member:03d}"
        target_member_str = f"LE2-{target_amoc}.{member_str}"
        
        # Set up strict local storage folder for this specific member
        member_download_dir = os.path.join(base_download_destination, target_amoc, member_str)
        os.makedirs(member_download_dir, exist_ok=True)
        
        print("\n" + "="*80)
        print(f"Processing Member: {target_member_str}")
        print(f"Destination: {member_download_dir}")
        print("="*80)

        # 3. Filter files matching this specific member
        matching_files = [file_name for file_name in master_file_lines if target_member_str in file_name]
        print(f"Found {len(matching_files)} total historical and future files for this member.")

        # 4. Process downloads for this member
        for files in matching_files:
            # Generate and clean URL
            raw_url = f"{download_UCAR_path}{files}"
            clean_url = raw_url.strip("'")
            
            # Extract base file name
            file_name = os.path.basename(clean_url)
            local_save_path = os.path.join(member_download_dir, file_name)
            
            # Skip if already downloaded completely
            if os.path.exists(local_save_path):
                print(f"  [Skipping] {file_name} already exists.")
                continue

            print(f"  Downloading {file_name} ... ", end="", flush=True)
            
            attempt = 0
            success = False
            
            while attempt < MAX_RETRIES and not success:
                try:
                    with requests.get(clean_url, headers=headers, stream=True, timeout=30) as r:
                        r.raise_for_status() 
                        
                        # with open(local_save_path, "wb") as f:
                        #     for chunk in r.iter_content(chunk_size=8192):
                        #         if chunk: 
                        #             f.write(chunk)
                        with open(local_save_path, "wb") as f:
                            f.write(r.content)

                    success = True
                    print("done")
                    
                except (requests.exceptions.RequestException, ConnectionResetError) as e:
                    attempt += 1
                    if attempt < MAX_RETRIES:
                        time.sleep(5)
                    else:
                        print(f"\n  [ERROR] Failed to download {file_name} after {MAX_RETRIES} attempts. Error: {e}")
                        # Clean up incomplete file if it failed entirely
                        if os.path.exists(local_save_path):
                            os.remove(local_save_path)
    
    print ("All Task Completed!!!")


# ==================================================================================================================
# Example Usage:
# ==================================================================================================================
if __name__ == "__main__":

    # Define your paths
    txt_list = "/home/michsh/Z_Python/cesm_downloadable_files_list.txt"
    base_destination = "/data2/michsh/full_member_data"

    # Define what you want to download
    amoc_state = "1281"
    
    # Python lists don't preserve prefix zeroes for integers, 
    # but the function will convert them automatically into "001", "002", "010", etc.
    members_to_download = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] 

    # Run the function
    download_cesm_members(
        target_amoc=amoc_state,
        target_members=members_to_download,
        file_list_path=txt_list,
        base_download_destination=base_destination
    )
