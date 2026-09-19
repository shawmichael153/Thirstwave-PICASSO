# Thirstwave-PICASSO
Repository archiving the work done during the 2026 PICASSO REU. This work was in association with Mark Flanner and Lisa Nguyen.

# **The Evolution of Growing Season Thirstwave Characteristics Across the CONUS From Historical to Future Climate Conditions** 

## **Backround**

This project was conducted as part of the 2026 PICASSO Research Experience for Undergraduates Program at the University of Michigan and was supported by the National Science Foundation (Grant No. 2348598). The project was spearheaded by **Michael Shaw**, under the mentorship of **Mark Flanner** and in collaboration with **Lisa Nguyen**. 

The primary goal of this project was to expand the work of Kukal and Hobbins (2025), who introduced the concept of Thirstwaves as periods of anomalously high atmospheric evaporative demand. While traditional drought metrics primarily describe deficits in precipitation, soil moisture, or runoff, Thirstwaves focus on the atmospheric demand for water and therefore provide a complementary way of examining drought and hydrologic stress.  

We employed the use of the Community Earth System Model Version 2 Large Ensemble (CESM2) to investigate how Thirstwaves may change across the contagious United States under future climate conditions. CESM2’s future period (2015-2100) employs the use of the SSP3-7.0, or the Shared Socioeconomic Pathway 3-7.0 which represents a high-emissions future characterized by limited international cooperation, slower economic development, and relatively high greenhouse gas emissions. These emissions result in approximately 7.0 W/m^2 of radiative forcing by the year 2100.

The workflow developed during this project calculates daily reference short crop evapotranspiration (ETos), establishes climatological thresholds for atmospheric evaporative demand, identifies Thirstwave events, and derives event-level and grid-level statistics from the CESM2 simulations. The resulting datasets and analysis scripts are intended to provide a foundation for further investigation into the physical mechanisms, regional impacts, and potential applications of Thirstwaves. 

---

## **Project Objectives** 

The project was designed to investigate how Thirstwave characteristics evolve across the CONUS under CESM2's future SSP3-7.0 climate scenario. To accomplish this goal, we developed the following objectives: 

- Calculate daily reference short-crop evapotranspiration (ETos) across the CONUS using the ASCE standardized Penman-Monteith equation and CESM2 meteorological variables for all ensemble members across the historical and future simulation periods. 

- Establish a historical climatological ETos threshold by calculating the 90th percentile of historical daily ETos for each calendar day and CONUS grid cell using the CESM2 ensemble. A 15-day moving average was then applied to the daily percentile thresholds to account for the seasonal cycle of atmospheric evaporative demand. This climatology serves as the baseline for identifying anomalously high ETos and evaluating future Thirstwave conditions. 

- Identify Thirstwave events by locating periods when daily ETos exceeds the historical 90th-percentile threshold for at least three consecutive days. 

- Calculate Thirstwave characteristics, including event frequency, duration, and intensity, for each grid cell, ensemble member, and simulation period. 

- Develop a comprehensive catalog of Thirstwave events across the CONUS containing event dates, duration, intensity, frequency, and spatial information. 

- Examine regional differences in Thirstwave characteristics across the CONUS and determine how event behavior varies spatially. 

- Evaluate future changes in Thirstwave characteristics by comparing historical conditions with multiple periods throughout the CESM2 SSP3-7.0 simulation. 

- Establish a foundation for future investigation of the physical mechanisms, regional impacts, and potential applications of Thirstwaves. 

## Project Workflow and Associated Scripts

To investigate the evolution of Thirstwave characteristics across the CONUS, we developed a multi-step workflow using daily CESM2 Large Ensemble output. The workflow progressed from acquiring and organizing the raw climate model data to calculating atmospheric evaporative demand, establishing a historical climatological threshold, identifying individual Thirstwave events, and finally extracting event-level characteristics for analysis. 

### **1.) Acquire and Organize CESM2-LE Data**

Daily CESM2 Large Ensemble atmospheric data was obtained for the 80 ensemble members. Historical (1850-2014) and future SSP3-7.0 (2015-2100) simulations were organized by AMOC state and ensemble members. More on CESM2LE naming conventions can be found here: https://www.cesm.ucar.edu/community-projects/lens2.  

The meteorological variables required to calculate reference evapotranspiration were collected for each member, including: 

- Daily maximum temperature (TREFHTMX) 
- Daily minimum temperature (TREFHTMN) 
- Specific humidity (QREFHT) 
- Surface pressure (PS) 
- Net shortwave radiation (FSNS) 
- Net longwave radiation (FLNS) 
- Near-surface wind speed (WSPDSRFAV) 

Because of the size of the CESM2-LE 80-member dataset, custom Python download scripts were developed to ease the data transfer. These files are organized by time period (HIST/FTR), AMOC state (1231, 1251, 1281, 1301), Ensemble Member (20 per AMOC state), and decadal period. More on the data download process can be found in ```data_download.py```.



### **2.) Calculate Daily Short-Crop Reference Evapotranspiration**

The CESM2 meteorological variables were used to calculate daily reference short-crop evapotranspiration (ETos) using the ASCE standardized Penman-Monteith formulation. 

The calculation involved deriving: 

- Mean daily air temperature 
- Saturation vapor pressure 
- Actual vapor pressure from specific humidity 
- Vapor pressure deficit 
- Slope of the saturation vapor pressure curve 
- Psychrometric constant 
- Net radiation 
- Wind speed at 2 m 

These variables were combined to produce daily ETos values in units of mm/day for every CONUS grid cell across the historical and future simulations. The code for this section can be found in ```ET_os_Calc.py```. 

**Only the growing-season months of April (1st) through October (31st) were retained within the ETos NetCDF files for the Thirstwave analysis.**

### **3.) Establish the Historical ETos Climatology**

A historical baseline was developed to determine what constitutes anomalously high atmospheric evaporative demand. 

For each CESM2 ensemble member and grid cell, daily ETos values were grouped by calendar day and used to calculate the 90th percentile of ETos. A 15-day moving window was then applied to smooth the daily percentile threshold and account for the seasonal cycle of atmospheric evaporative demand. 

The ensemble members and historical years were subsequently combined to establish a common historical ETos climatology across the CONUS. This climatological threshold provides the baseline against which historical and future ETos conditions were evaluated. More on this can be found at ```90th_ZARR.py```. 

### **Transition to Thirstwave Event Analysis**

The first three stages of the workflow establish the primary datasets required for the Thirstwave analysis: daily ETos and the historical 90th-percentile ETos climatology. These steps follow a relatively direct progression from the original CESM2-LE data to the variables needed for event identification.

The remainder of the workflow becomes more computationally involved, as the daily ETos and historical threshold datasets are used to identify individual Thirstwave events and derive their characteristics. Therefore, the following sections provide a more detailed description of the code used to construct the intermediate Zarr datasets and final CSV event catalog, including how threshold exceedances were identified, how consecutive exceedances were grouped into individual events, and how event-level frequency, duration, and intensity metrics were ultimately derived.
