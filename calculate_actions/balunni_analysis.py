import geopandas as gpd
import numpy as np
import shapely as shp
import pandas as pd
import rasterio
from pathlib import Path
from rasterstats import zonal_stats
from balunni_functions import stitchoutputs

output_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Test Peatland Extraction\\Outputs\\"
input_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Test Peatland Extraction\\Inputs\\"
data_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\"

## Stitch priority data together if needed
#peatland_stitch = stitchoutputs(Path(output_path), Path(output_path), search_text="peatland_50k", file_pattern= "*.csv")
#elevation_stitch = stitchoutputs(Path(output_path), Path(output_path), id_column= "id", search_text="elevation_50k", file_pattern= "*.csv")
peatland_stitch = pd.read_csv(Path(output_path)/ "peatland_50k_combined.csv")

# Read in stocking data from DSD - USED THE LPIS_FIELD DATA INSTEAD OF THE PARQUET DATA TO CREATE BATCHES!
stocking_data = gpd.read_parquet(Path(data_path) / "Nutrient Loading per field\\jncc_2024_extract.parquet")
stocking_data['field_id_code'] # This is the unique field id

# Check differences between geometry area and maximum eligible area claimed under scheme
stocking_data["area_diff"] = stocking_data["geometry_area"] - stocking_data["field_mea_ha"]

print(stocking_data["area_diff"].describe()) # Mostly very minor differences here, but some much larger ones. Suggest using geometry area

# Create new geometry area column using boundaries here and check how this compares with old geometry column
stocking_data["geometry_area_new_ha"] = stocking_data.geometry.area / 10000 

# Check differences between new and old geometry area
stocking_data["geometry_area_diff"] = stocking_data["geometry_area_new_ha"] - stocking_data["geometry_area"]

stocking_data.loc[stocking_data["geometry_area"].isna()]
stocking_data["geometry_area"].isna().sum()

print(stocking_data["geometry_area_diff"].describe()) # identical, suggest using geometry_area moving forward in calculations

# Read in LFA data 
lfa_data = pd.read_csv(Path(data_path)/ "LPIS_Fields\\2024_field_data_extract.csv")

# Read in peatland and elevation data
jhi_peat = gpd.read_file(Path(input_path) / "JHI_Peatland_Processed.gpkg")
with rasterio.open("O:\\EAT\\EOMonitoringApplications\\NorthernIreland2022\\Topography\\outputs\\NI_DTM_10m_TM65_2023_merged.tif") as src:
    dem = src.read(1)
    transform = src.transform
    nodata = src.nodata

# Join datasets up - SOMETHING ODD HAPPENING HERE BECAUSE geometry_area is NaN for some parcels. This is because of using LPIS Fields rather than parcel extract so there are some mismatches
stocking_peatland = peatland_stitch.join(stocking_data.set_index("field_id_code"), on="parcel_id").join(lfa_data.set_index("FieldNo"), on="parcel_id")

# Get relevant columns to subset data
peatland_cols = [
    'parcel_id',
    'layer',
    'class',
    'percent',
    'geometry_area'
]

# Relevant stocking data columns
headcount_cols = stocking_peatland.loc[
    :, 'app_bc_cow_headcount':'app_sh_12m_mr_headcount'
].columns

# Relevant lfa columns
lfa_cols = lfa_data.loc[
    :, 'BUSID':'Land Type'
].columns

# subset columns using lists above and filter to just JHI data
clean_stocking_peatland = stocking_peatland.loc[(stocking_peatland["layer"] == "JHI_Peatland"), peatland_cols + headcount_cols.tolist() + lfa_cols.tolist()]

# Extract rows corresponding to JHI_peatland with 100% class coverage for use in stocking density calculations
##SOME OF THESE ARE NaN for geometry_area for some reason, check this in QGIS e.g. 2/001/003/9
clean_stocking_peatland_100_pct = clean_stocking_peatland.loc[(clean_stocking_peatland["percent"] >= 100)]

# Check that no parcel IDs appear twice for calculations
duplicate_check = clean_stocking_peatland_100_pct["parcel_id"].duplicated(keep=False)
print(clean_stocking_peatland_100_pct.loc[duplicate_check])

# Get counts of parcels used in calculations for sample size stats
class_counts = (
    clean_stocking_peatland_100_pct
    .groupby("class")["Land Type"]
    .value_counts()
    .reset_index()
)

class_counts.columns = ["class", "Land Type", "count"]

# Write out
class_counts.to_csv(Path(output_path) / "peatland_land_type_sample_sizes_NI.csv")

# Now calculate the average stocking density per hectare
# Sum livestock counts and area by class
livestock_totals = (
    clean_stocking_peatland_100_pct
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .sum()
)

area_totals = (
    clean_stocking_peatland_100_pct
    .groupby(["class", "Land Type"])["geometry_area"]
    .sum()
)

# Divide each livestock total by total area
averages = livestock_totals.div(area_totals, axis=0)

print(averages)

averages.to_csv(Path(output_path) / "peatland_land_type_avg_stocking_densities_NI.csv")

## Work out what the area of each peatland class is in upland v lowland
# This is done using a zonal stats approach to work out what proportion of each class is above/below a 150m threshold
# The original JHI data is used here in order to capture the entire area of the map, rather than just that which overlaps the parcel data we have
# First create the binary raster from the DEM
threshold = 150
class_col = "Class"

binary = np.where(
    np.isnan(dem),
    255,
    np.where(dem > threshold, 1, 0)
).astype("uint8")

# Calculate raster stats, mean in this case will be the proportion of pixels above the threshold
stats = zonal_stats(
    vectors=jhi_peat,
    raster=binary,
    affine=transform,
    stats=["mean"],
    nodata=255
)

# Add these stats back to the JHI peat map to calculate percentage above/below thresholds
jhi_peat["pct_above"] = [
    s["mean"] * 100 if s["mean"] is not None else np.nan
    for s in stats
]

# Calculate other columns for above/below to work out total areas
jhi_peat["pct_below"] = 100 - jhi_peat["pct_above"]

jhi_peat["area_ha"] = jhi_peat.geometry.area / 10000

jhi_peat["area_above_ha"] = (
    jhi_peat["area_ha"] *
    jhi_peat["pct_above"] / 100
)

jhi_peat["area_below_ha"] = (
    jhi_peat["area_ha"] *
    jhi_peat["pct_below"] / 100
)

# Generate a summary output for each peatland class
summary_upland = (
    jhi_peat
    .groupby(class_col)
    .agg(
        total_area_ha=("area_ha", "sum"),
        area_above_ha=("area_above_ha", "sum"),
        area_below_ha=("area_below_ha", "sum")
    )
    .reset_index()
)

summary_upland["pct_above"] = (
    100 *
    summary_upland["area_above_ha"] /
    summary_upland["total_area_ha"]
)

summary_upland["pct_below"] = (
    100 - summary_upland["pct_above"]
)

# write out summary spreadsheet 
#summary_upland.to_csv(Path(output_path) / "peatland_upland_areas_NI.csv")

# write out binary raster generated earlier to check this was done appropriately in QGIS 
with rasterio.open("O:\\EAT\\EOMonitoringApplications\\NorthernIreland2022\\Topography\\outputs\\NI_DTM_10m_TM65_2023_merged.tif") as src:

    profile = src.profile.copy()

    profile.update(
        dtype="uint8",
        count=1,
        compress="lzw",
        nodata=255
    )

    with rasterio.open(
        Path(data_path) / "OSNI_10m_DTM\\150m_upland_binary.tif",
        "w",
        **profile
    ) as dst:
        dst.write(binary, 1)

## Get proportion of peatland classes in each land classification type


# We already have a summary output for peatland classes above/below upland threshold with total area in ha - summary_upland
# So just need to work out the proportion of this area that overlaps with different classifications. Add a column to the data to get area of each peat class
clean_stocking_peatland["peat_area_ha"] = (
    (clean_stocking_peatland["percent"] / 100) * clean_stocking_peatland["field_mea_ha"]
)

# Get total area of each land classification from parcel data, making sure each parcel is only chosen once 
total_classification_areas = (
    clean_stocking_peatland
    .groupby(["parcel_id", "Land Type"])["peat_area_ha"]
    .sum()
)