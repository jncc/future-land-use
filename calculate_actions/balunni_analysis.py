## Script Name: BALUNNI Analysis
## 
## Author: Rory Barber, Ecosystems Analysis
## 
## Contact (if different from above): 
## 
## Date Created: 2026-08-20
## 
## Date Last Modified: 2026-10-14
##
## Licence: Open Government Licence
## 
## Abstract: This script is used to do further analysis from the extraction of peatland overlaps with land parcels in Northern Ireland. It is split into multiple parts in order to 
##           generate average stocking densities for peatland-land classification combos, estimate the proportion of peatland classes above and below the upland line and the types of crops grown on the crops class.
##           These data will then be used to generate Marginal Abatement Cost Curves in further economic analyses, estimating costs/benefits of peatland restoration on different land types 
##
## Python version 3.13.11
## Dependencies:
##    
## geopandas        numpy
## pandas           os    
## shapely          rasterio
## matplotlib       pathlib 
## rasterstats      balunni_functions
## ############################## ##


import geopandas as gpd
import numpy as np
import shapely as shp
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from pathlib import Path
from rasterstats import zonal_stats
from balunni_functions import stitchoutputs

pd.set_option("display.max_columns", None)

## Define paths and read in data for analysis 
extraction_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Final Peatland Extraction\\Outputs\\"
input_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Final Peatland Extraction\\Inputs\\"
output_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Outputs\\"
data_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\"

# Read in LFA and stocking data 
lfa_data = pd.read_csv(Path(data_path)/ "LPIS_Fields\\2024_field_data_extract.csv")
stocking_data = gpd.read_parquet(Path(data_path) / "Nutrient Loading per field\\jncc_2024_extract.parquet")
lpis_not_in_stocking = gpd.read_file((Path(input_path) / "Non-stocking Parcels\\parcel_batch_001.gpkg"))

# Read in peatland and elevation data
jhi_peat = gpd.read_file(Path(input_path) / "JHI_Peatland_Processed.gpkg")
jhi_raw = gpd.read_file(Path(data_path) / "Peatland\\Peatland.gpkg")
with rasterio.open("O:\\EAT\\EOMonitoringApplications\\NorthernIreland2022\\Topography\\outputs\\NI_DTM_10m_TM65_2023_merged.tif") as src:
    dem = src.read(1)
    transform = src.transform
    nodata = src.nodata

# Read in Ards peninsula data for later filtering of cropland data - a known issue with JHI crop class. Plot it
ards = gpd.read_file(Path(data_path) / "geography-dz2021-esri-shapefile\\DZ2021.shp", where="DEA2014_nm = 'Ards Peninsula'")
ards.plot()
plt.show()

# Create single geometry for futher filtering of parcels
ards_geom = ards.union_all()

## STEP 1: Stitch priority data outputs together if needed using pre-defined function
#peatland_stitch = stitchoutputs(Path(extraction_path), Path(extraction_path), search_text="peatland_50k", file_pattern= "*.csv")
#elevation_stitch = stitchoutputs(Path(extraction_path), Path(extraction_path), id_column= "id", search_text="elevation_50k", file_pattern= "*.csv")
peatland_stitch = pd.read_csv(Path(extraction_path)/ "peatland_50k_combined.csv")
peatland_non_stocking = pd.read_csv(Path(extraction_path)/ "peatland_non-stocking_parcels_perecentages\\priority_scores_peatland_non-stocking_parcels_perecentages.csv").rename(columns={"id.1": "parcel_id"})

## STEP 2: Calculate the average stocking density of each livestock category on each combination of peatland and land classification
# Note that the livestock density on Crops peat class is being ignored in the final analysis, so have not removed Ards peninsula at this stage
# Check for duplicate parcels, CRS and unqiue ID columns
duplicate_stocking = stocking_data["field_id_code"].duplicated(keep=False)
print(stocking_data.loc[duplicate_stocking]) # None
print(stocking_data.crs) #29902 like peatland priority data
stocking_data['field_id_code'] # This is the unique field id

duplicate_lfa = lfa_data["FieldNo"].duplicated(keep=False)
print(lfa_data.loc[duplicate_lfa]) # There are quite a few duplicate IDs here where parcels have claimed under multiple businesses numbers or have multiple crop codes

# # Get summaries of the different duplicates involved in the data 
# duplicate_summary = []

# for fieldno, group in lfa_data.groupby("FieldNo"):

#     if len(group) == 1:
#         continue

#     duplicate_summary.append({
#         "FieldNo": fieldno,
#         "n_records": len(group),
#         "n_BUSID": group["BUSID"].nunique(),
#         "n_UsageCode": group["UsageCode"].nunique(),
#         "areaclaimed_same": group["AreaClaimed"].nunique() == 1,
#         "areadetermined_same": group["AreaDetermined"].nunique() == 1,
#         "meaarea_same": group["MEAArea"].nunique() == 1,
#     })

# duplicate_summary = pd.DataFrame(duplicate_summary)

# ## Handling the duplicate records in LFA data - necessary if we are only using IDs and mea area from the stocking_data?
# ## So we want to remove duplicates which have two businesses claiming on that field but all other columns are the same
# ## Where the MEA for a field differs we should remove these results entirely as not sure which is correct
# ## Where there are different crops being grown in a field we want to keep these records so we can do crop proportion calculations, but only use the MEA once 
# ## For overall peat x land type combo area calculations we want to use geometry_area of parcel, so this shouldn't matter too much

# # Create new column to review duplicates in the data and classify them. We will apply the rules above to this afterwards
# duplicate_summary["duplicate_type"] = "REVIEW"

# # Rule 1:
# # Multiple BUSIDs but everything else identical
# duplicate_summary.loc[
#     (duplicate_summary["n_BUSID"] > 1)
#     & (duplicate_summary["n_UsageCode"] == 1)
#     & duplicate_summary["areaclaimed_same"]
#     & duplicate_summary["areadetermined_same"]
#     & duplicate_summary["meaarea_same"],
#     "duplicate_type"
# ] = "BUSID_ONLY"

# # Rule 2:
# # Different MEA values for same FieldNo
# duplicate_summary.loc[
#     ~duplicate_summary["meaarea_same"],
#     "duplicate_type"
# ] = "MEA_CONFLICT"

# # Rule 3:
# # Same field, multiple crop types, MEA consistent
# duplicate_summary.loc[
#     (duplicate_summary["n_UsageCode"] > 1)
#     & duplicate_summary["meaarea_same"],
#     "duplicate_type"
# ] = "MULTIPLE_CROPS"

# Check differences between geometry area and maximum eligible area claimed under scheme
stocking_data["area_diff"] = stocking_data["geometry_area"] - stocking_data["field_mea_ha"]

print(stocking_data["area_diff"].describe()) # Mostly very minor differences here, but some much larger ones. Use MEA for stocking calculations but geometry area for peatland coverage

# Create new geometry area column using boundaries here and check how this compares with old geometry_area column
stocking_data["geometry_area_new_ha"] = stocking_data.geometry.area / 10000 

# Check differences between new and old geometry area
stocking_data["geometry_area_diff"] = stocking_data["geometry_area_new_ha"] - stocking_data["geometry_area"]

# Check there are no NAs 
stocking_data.loc[stocking_data["geometry_area"].isna()]
stocking_data["geometry_area"].isna().sum()

print(stocking_data["geometry_area_diff"].describe()) # identical, suggest using geometry_area moving forward in other calculations not linked to headcounts or nutrients

# Join datasets up, making sure to put geopandas first to retain geometries
# doing from the peatland extraction the output contains 2,087,320 and 140,682 rows respectively
stocking_peatland = stocking_data.join(peatland_stitch.set_index("parcel_id"), on="field_id_code", how="right").join(lfa_data.set_index("FieldNo"), on="field_id_code").rename(columns={"field_id_code":"parcel_id"})
non_stocking_peatland = lpis_not_in_stocking.join(peatland_non_stocking.set_index("parcel_id"), on ="ID", how="right").join(lfa_data.set_index("FieldNo"), on="ID").rename(columns={"ID":"parcel_id"})
stocking_peatland["parcel_id"].nunique() #577,833
non_stocking_peatland["parcel_id"].nunique() #38,664

# Count number of parcels retained and make sure IDs matches original stocking_data, should be equal
peatland_ids = set(stocking_peatland["parcel_id"].dropna())
stocking_ids = set(stocking_data["field_id_code"].dropna())
non_stocking_peatland_ids = set(peatland_non_stocking["parcel_id"].dropna())
lfa_ids = set(lfa_data["FieldNo"].dropna())

# Crosscheck that parcels used in peatland extraction have all made it over
non_stocking_ids = set(lpis_not_in_stocking["ID"].dropna())

if peatland_ids != stocking_ids:
    print("Error - parcel IDs do not match between datasets")

    missing_from_peatland = stocking_ids - peatland_ids
    missing_from_stocking = peatland_ids - stocking_ids

    print(f"Missing from peatland: {len(missing_from_peatland)}") # One parcel missing which is a tiny island in an estuary - none of the peatland datasets overlap and no reported livestock so ignoring
    print(f"Missing from stocking: {len(missing_from_stocking)}")

if non_stocking_ids != non_stocking_peatland_ids:
    print("Warning - parcel IDs do not match between datasets")

    missing_from_non_stocking = non_stocking_peatland_ids - non_stocking_ids
    missing_from_peatland_non_stocking = non_stocking_ids - non_stocking_peatland_ids

    print(f"Missing from Peatland: {len(missing_from_peatland_non_stocking)}") # Should be 0, but is 2, these are 3/108/085/54 and 55. Also in estuary with no peatland overlapping so fine.
    print(f"Missing from non-stocking: {len(missing_from_non_stocking)}")  # Should be 0

# Subset lfa dataset
# lfa_not_in_stocking = (lfa_data.loc[
#     ~lfa_data["FieldNo"].isin(stocking_data["field_id_code"])
# ].drop_duplicates(subset=["FieldNo"]))
# print(lfa_not_in_stocking)
# print(lfa_not_in_stocking["MEAArea"].sum()) # 61k ha from 42k parcels not in the stocking data
# #lfa_not_in_stocking.to_csv((Path(output_path) / "LPIS_Fields_no_stocking.csv")) # This data is then used to re-process LPIS fields for peatland classification outside of stocking areas

# Check area columns are still intact - both should return nothing
mea_nas = stocking_peatland["field_mea_ha"].isna().sum()
field_nas = stocking_peatland["geometry_area"].isna().sum()

# Now remove the Ards Peninsula from the datasets where the Peat class is 'Crops'. This is flagged in the JHi documentation as the area where a significant overestimation of the Crops peat class is likely to occur
# Remove the Ards Peninsula from the stocking and non-stocking spatial LPIS field dataset, first get Crops subset of datasets
crops_stocking = stocking_peatland[stocking_peatland["class"] == "Crops"]
crops_non_stocking = non_stocking_peatland[non_stocking_peatland["class"] == "Crops"]

# Identify those which overlap with Ards
overlaps_stocking = crops_stocking[crops_stocking.intersection(ards_geom).area > 0]
overlaps_stocking["parcel_id"].nunique() #4,225
overlaps_non_stocking = crops_non_stocking[crops_non_stocking.intersection(ards_geom).area > 0]
overlaps_non_stocking["parcel_id"].nunique() #206

# Filter from the original dataset - note that this will remove some parcels which are 
no_ards_stocking_peatland = stocking_peatland.loc[~stocking_peatland.index.isin(overlaps_stocking.index)]
no_ards_stocking_peatland["parcel_id"].nunique() #573,608, exactly 4,225 parcels fewer
no_ards_non_stocking_peatland = non_stocking_peatland.loc[~non_stocking_peatland.index.isin(overlaps_non_stocking.index)]
no_ards_non_stocking_peatland["parcel_id"].nunique() #38,458, exactly 206 parcels fewer

# Plot for comparison of before after
no_ards_stocking_peatland.plot()
plt.show()

stocking_peatland.plot()
plt.show()

# Get relevant columns to subset data
peatland_cols = [
    'parcel_id',
    'layer',
    'class',
    'percent'
]

# parcel area and geometry columns
area_cols = [
    'geometry_area',
    'field_mea_ha' 
]

# Only needed for non stocking data
lpis_geometry = [
    'geometry'
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
clean_stocking_peatland = no_ards_stocking_peatland.loc[(no_ards_stocking_peatland["layer"] == "JHI_Peatland"), peatland_cols + area_cols + headcount_cols.tolist() + lfa_cols.tolist()]
clean_non_stocking_peatland = no_ards_non_stocking_peatland.loc[(no_ards_non_stocking_peatland["layer"] == "JHI_Peatland"), peatland_cols + lfa_cols.tolist() + lpis_geometry]
clean_stocking_peatland["parcel_id"].nunique() #235,777 parcels overlap with JHI data, 231,552 without the ards peninsula (4,225 parcels) - 4,225 unique parcels in overlaps_stocking 
clean_non_stocking_peatland["parcel_id"].nunique() #15,525 parcels with no stocking data overlap with JHI, now 15,319 (206 parcels) - matches 206 unique parcel IDS from overlaps 

# Extract rows corresponding to JHI_peatland with 90% class coverage for use in stocking density calculations
clean_stocking_peatland_90_pct = clean_stocking_peatland.loc[(clean_stocking_peatland["percent"] >= 90)]

# Check that no parcel IDs appear twice for calculations - some do because of different business codes in LFA data etc. This is fine but we need to make sure the headcount/area is only considered once for each parcel
duplicate_check = clean_stocking_peatland_90_pct["parcel_id"].duplicated(keep="first")
print(clean_stocking_peatland_90_pct.loc[duplicate_check])
clean_stocking_peatland_90_pct.drop_duplicates("parcel_id", inplace=True) # Retain only one parcel for stocking density calculations

# # Investigate these further
# stocking_data["field_id_code"].value_counts().loc[
#     lambda x: x > 1
# ]

# # Seems to be duplicate values in the LFA data causing problems here. We only want one classification and crop grown per parcel from this data so suggest cleaning duplicate records first?
# lfa_data["FieldNo"].value_counts().loc[
#     lambda x: x > 1
# ]

# Get counts of parcels used in calculations for sample size stats
class_counts = (
    clean_stocking_peatland_90_pct
    .groupby("class")["Land Type"]
    .value_counts()
    .reset_index()
)

class_counts.columns = ["class", "Land Type", "parcel_count"]

# Write out separately if desired, otherwise append to stats in below commans
#class_counts.to_csv(Path(output_path) / "peatland_land_type_sample_sizes_NI_90_pct.csv")
#clean_stocking_peatland_90_pct.to_csv(Path(output_path) / "peatland_land_type_parcels_NI_90_pct_no_ards.csv")

# Now calculate the stocking density per hectare
# Sum livestock counts and area by class
livestock_totals = (
    clean_stocking_peatland_90_pct
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .sum()
)

# We want mea areas for stocking density calculations as this is the area where animals graze
area_totals = (
    clean_stocking_peatland_90_pct
    .groupby(["class", "Land Type"])["field_mea_ha"]
    .sum()
)

# Divide each livestock total by total area
densities = livestock_totals.div(area_totals, axis=0)

# Add parcel counts for completeness
densities = densities.merge(class_counts, on=["class", "Land Type"])
densities = densities[
    ["class", "Land Type", "parcel_count"] +
    [c for c in densities.columns
     if c not in ["class", "Land Type", "parcel_count"]]
]

print(densities)

#densities.to_csv(Path(output_path) / "peatland_land_type_stocking_densities_NI_90_pct_no_ards.csv")

# Alternative approach - calculate stocking density on each of the parcels and then take the average of these 
density_df = clean_stocking_peatland_90_pct.copy()

for livestock in headcount_cols:
    density_df[livestock] = (
        density_df[livestock] /
        density_df["field_mea_ha"]
    )

# Get some summary statistics and then convert this into long format 
density_summary = (
    density_df
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .agg([
        ("min", "min"),
        ("p10", lambda x: x.quantile(0.1)),
        ("mean", "mean"),
        ("p90", lambda x: x.quantile(0.9)),
        ("max", "max"),
    ])
)

density_summary = (
    density_summary
    .stack(level=1, future_stack=True)
    .rename_axis(index=["class", "Land Type", "statistic"])
    .reset_index()
)

# Add in parcel counts
density_summary = density_summary.merge(class_counts, on=["class", "Land Type"])
density_summary = density_summary[
    ["class", "Land Type", "parcel_count", "statistic"] +
    [c for c in densities.columns
     if c not in ["class", "Land Type", "parcel_count", "statistic"]]
]

density_summary.head()

#density_summary.to_csv(Path(output_path) / "peatland_land_type_parcel_stocking_densities_stats_NI_90_pct_no_ards.csv")

# Analysis also wants to know the average stocking densities for intensive/extensive grassland combined, eroding modified bogs drained/undrained and non-eroding modified bogs drained/undrained
merged_density_df = density_df.copy()

# combine respective categories 
groupings = {
    "Grassland, extensive": "Grassland",
    "Grassland, intensive": "Grassland",
    "Modified bog, eroding, drained": "Modified bog, eroding",
    "Modified bog, eroding, undrained": "Modified bog, eroding",
    "Modified bog, grassland/ heather, drained": "Modified bog, grassland/heather",
    "Modified bog, grassland/ heather, undrained": "Modified bog, grassland/heather"
}

merged_density_df["class"] = merged_density_df["class"].replace(groupings)
merged_density_df.head()

# Get some summary statistics and then convert this into long format 
merged_density_summary = (
    merged_density_df
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .agg([
        ("min", "min"),
        ("p10", lambda x: x.quantile(0.1)),
        ("mean", "mean"),
        ("p90", lambda x: x.quantile(0.9)),
        ("max", "max"),
    ])
)

merged_density_summary = (
    merged_density_summary
    .stack(level=1, future_stack=True)
    .rename_axis(index=["class", "Land Type", "statistic"])
    .reset_index()
)

# Add in total parcel numbers used in calculation of above stats
merged_density_parcel_count = (
    merged_density_df
    .groupby("class")["Land Type"]
    .value_counts()
    .rename("parcel_count")
    .reset_index()
)

# Join to parcel counts and reorder columns
merged_density_summary = merged_density_summary.merge(merged_density_parcel_count, on=["class", "Land Type"])
merged_density_summary = merged_density_summary[
    ["class", "Land Type", "parcel_count", "statistic"] +
    [c for c in merged_density_summary.columns
     if c not in ["class", "Land Type", "parcel_count", "statistic"]]
]

merged_density_summary.head()
#merged_density_summary.to_csv(Path(output_path) / "peatland_land_type_parcel_stocking_densities_stats_NI_90_pct_merged_no_ards.csv")

## STEP 3: Work out what the area of each peatland class is in upland v lowland
# This is done using a zonal stats approach to work out what proportion of each class is above/below a 150m threshold
# The original JHI data is used here in order to capture the entire area of the map, rather than just that which overlaps the parcel data we have
# First create the binary raster from the DEM
threshold = 150
class_col = "Class"

# Set NAs to 255 so that they aren't included in the 0 calculation for estimating proportions of classes above/below threshold
binary = np.where(
    np.isnan(dem),
    255,
    np.where(dem > threshold, 1, 0)
).astype("uint8")

# Filter out Ards Peninsula from JHI Crops data 
jhi_crops = jhi_peat[jhi_peat["Class"] == "Crops"] #27,384 polygons
jhi_crops["area_ha"] = jhi_crops.geometry.area / 10000
sum(jhi_crops["area_ha"]) #15,644 ha

# Identify those which overlap with Ards 
ards_crops = jhi_crops[jhi_crops.intersection(ards_geom).area > 0] #2,595 polygons
sum(ards_crops["area_ha"]) #3,788 ha being removed from the JHI data

# Filter from the original dataset and write out to check
no_ards_crops_jhi = jhi_peat.loc[~jhi_peat.index.isin(ards_crops.index)]
no_ards_crops_jhi.to_file(Path(input_path) / "JHI_Peatland_no_ards_crops.gpkg")

# Plot for comparison of before after
no_ards_crops_jhi.plot()
plt.show()

# write out binary raster generated earlier to check this was done appropriately in QGIS - O:\EAT\Ecosystems Analysis\BALLUNI\CBA Analysis\Upland_Data_Check.qgz
# with rasterio.open("O:\\EAT\\EOMonitoringApplications\\NorthernIreland2022\\Topography\\outputs\\NI_DTM_10m_TM65_2023_merged.tif") as src:

#     profile = src.profile.copy()

#     profile.update(
#         dtype="uint8",
#         count=1,
#         compress="lzw",
#         nodata=255
#     )

#     with rasterio.open(
#         Path(data_path) / "OSNI_10m_DTM\\150m_upland_binary.tif",
#         "w",
#         **profile
#     ) as dst:
#         dst.write(binary, 1)

# Calculate raster stats, mean in this case will be the proportion of pixels in a parcel above the threshold
stats = zonal_stats(
    vectors=no_ards_crops_jhi,
    raster=binary,
    affine=transform,
    stats=["mean"],
    nodata=255
)

# Add these stats back to the JHI peat map to calculate percentage above/below thresholds
no_ards_crops_jhi["pct_above"] = [
    s["mean"] * 100 if s["mean"] is not None else np.nan
    for s in stats
]

# Calculate other columns for above/below to work out total areas
no_ards_crops_jhi["pct_below"] = 100 - no_ards_crops_jhi["pct_above"]

no_ards_crops_jhi["area_ha"] = no_ards_crops_jhi.geometry.area / 10000
# jhi_raw["area_ha"] = jhi_raw.geometry.area / 10000
# summary_raw = (
#     jhi_raw
#     .groupby("Class")
#     .agg(
#         total_area_ha=("area_ha", "sum")
#     )
#     .reset_index()
# )

no_ards_crops_jhi["area_above_ha"] = (
    no_ards_crops_jhi["area_ha"] *
    no_ards_crops_jhi["pct_above"] / 100
)

no_ards_crops_jhi["area_below_ha"] = (
    no_ards_crops_jhi["area_ha"] *
    no_ards_crops_jhi["pct_below"] / 100
)

# Generate a summary output for each peatland class
summary_upland = (
    no_ards_crops_jhi
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
#summary_upland.to_csv(Path(output_path) / "peatland_upland_areas_NI_no_ards.csv", index=False)
summary_upland = pd.read_csv(Path(output_path) / "peatland_upland_areas_NI.csv")

## STEP 4: Get proportion of peatland classes in each land classification type
# We already have a summary output for peatland classes above/below upland threshold with total area of each class in ha - summary_upland
# So just need to work out the proportion of this total area that overlaps with different land classifications. Add a column to the data to get area of each peat class
clean_stocking_peatland["peat_area_ha"] = (
    (clean_stocking_peatland["percent"] / 100) * clean_stocking_peatland["geometry_area"] # use geometry area as looking at overall proportions not claimed areas
)

# Also do this for non-stocking areas - first create convert back to GeoPandas Dataframe and create geometry area column
# clean_non_stocking_peatland = gpd.GeoDataFrame(
#     clean_non_stocking_peatland,
#     geometry="geometry",
#     crs="EPSG:29902"  # or whatever CRS is correct
# )
clean_non_stocking_peatland["geometry_area"] = clean_non_stocking_peatland.geometry.area / 10000 
clean_non_stocking_peatland["peat_area_ha"] = (
    (clean_non_stocking_peatland["percent"] / 100) * clean_non_stocking_peatland["geometry_area"] # use geometry area as looking at overall proportions not claimed areas
)

# Messy bind as column names are not all the same 
clean_lpis_peatland = pd.concat(
    [clean_stocking_peatland, clean_non_stocking_peatland],
    ignore_index=True
)

#clean_lpis_peatland.to_csv(Path(output_path) / "lpis_peatland_check.csv")

# Get total area of each land classification from parcel data, for each peatland class x land type combo - CHANGE IF ONLY WANTING STOCKING DATA
peat_classification_areas = (
    clean_lpis_peatland
    .groupby(["class", "Land Type"])["peat_area_ha"]
    .sum()
    .reset_index()
)

# Merge this with summary_upland data 
total_peat_areas = (
    peat_classification_areas
    .merge(
        summary_upland.rename(columns={"Class": "class"})[
            ["class", "total_area_ha"]
        ],
        on="class",
        how="left"
    )
)

# Calculate area and percentage within each land type
total_peat_areas["pct_of_peat_class"] = (
    100 *
    total_peat_areas["peat_area_ha"] /
    total_peat_areas["total_area_ha"]
)

# Calculate residual area for each peat class that falls outside parcels
outside_rows = (
    total_peat_areas
    .groupby("class")
    .agg(
        classified_area_ha=("peat_area_ha", "sum"),
        total_area_ha=("total_area_ha", "first")
    )
    .reset_index()
)

outside_rows["peat_area_ha"] = (
    outside_rows["total_area_ha"]
    - outside_rows["classified_area_ha"]
)

outside_rows["pct_of_peat_class"] = (
    100 *
    outside_rows["peat_area_ha"] /
    outside_rows["total_area_ha"]
)

# Add this back into the main dataframe by adding a new row under each Peat class to give percentages
outside_rows["Land Type"] = "Outside parcel boundary"

# Keep only columns present in main dataframe
outside_rows = outside_rows[
    [
        "class",
        "Land Type",
        "peat_area_ha",
        "total_area_ha",
        "pct_of_peat_class"
    ]
]

# Match columns from main table
total_peat_areas = total_peat_areas[
    [
        "class",
        "Land Type",
        "peat_area_ha",
        "total_area_ha",
        "pct_of_peat_class"
    ]
]

# Append the outside-boundary rows
total_peat_areas = pd.concat(
    [total_peat_areas, outside_rows],
    ignore_index=True
)

# Check these sum to 100%
check = (
    total_peat_areas
    .groupby("class")["pct_of_peat_class"]
    .sum()
)

print(check)

# Rearrange row order and write
#total_peat_areas.sort_values(by=['class']).to_csv(Path(output_path) / "peatland_land_type_area_proportions_all_lpis_no_ards.csv", index=False)

## STEP 5: Calculate the percentages of different crop types grown on cropland class in the JHI data 
# We have the total area of Crops class from summary_upland
clean_cropland_peat = clean_lpis_peatland.loc[(clean_lpis_peatland["class"] == "Crops")] # 33,238 parcels, now 35,728 parcels. 31,241 without ards
sum(clean_cropland_peat["peat_area_ha"]) #10342 ha, tallies because outside_rows value for crops is 1514ha

# Some parcels have multiple crops being grown on them, inspect these to identify values to remove from proportion estimates
multi_crops = clean_cropland_peat["parcel_id"].duplicated(keep=False)
print(clean_cropland_peat.loc[(multi_crops)]) # so UsageCode is the key column containing info, 657 parcels now 800 parcels with non-stocking. 701 with no ards
#multi_crops.to_csv(Path(output_path) / "crops_grown_on_peatland_crops_class_all_lpis_multi_crops_no_ards.csv")

# Problem we have is that the peatland area is not necessarily 100% of the parcel, 
# where we have multiple crops we don't know how this aligns with the peatland coverage
# so we actually need to only include those with 100% coverage (much smaller sample) or just remove those where multiple crops are recorded (~2% parcels). Suggest the latter
clean_single_cropland_peat = clean_cropland_peat.drop_duplicates(subset="parcel_id", keep=False) # 32,581 parcels now 34,928 with non-stocking

# Generate some stats 
clean_single_cropland_peat["area_diff"] = (
    clean_single_cropland_peat["geometry_area"] - clean_single_cropland_peat["AreaClaimed"]
)

sum(clean_single_cropland_peat["peat_area_ha"]) #9627ha so lost 715ha from multi-crop locations. About 93% of the peat class area

cropland_parcel_summary = (
    clean_single_cropland_peat["area_diff"]
    .agg([
        "min",
        "mean",
        "max"
    ])
)

#clean_single_cropland_peat.to_csv(Path(output_path) / "single_crops_grown_on_peatland_no_ards_parcels.csv")
#cropland_parcel_summary.to_csv(Path(output_path) / "area_ha_differences_single_cropland_parcels.csv")

# Group by UsageCode and sum peat_area_ha, then merge with total areas of each class above to get total area of Crops class, pulling over area outside parcel data
# peat_area_ha is calculated from the geometry area rather than ME Area, so likely to be inflated but we have agreed that this assumption is OK because we just need indicative proportions which are then multipled by actual peat areas from JHI
crop_proportions = (
    clean_single_cropland_peat
    .groupby(["class","Land Type","UsageCode"], as_index=False)["peat_area_ha"]
    .sum()
    .rename(columns={"peat_area_ha": "crop_area_ha"})
)

crops_outside = (
    total_peat_areas
    .loc[(total_peat_areas["Land Type"] == "Outside parcel boundary") & (total_peat_areas["class"] == "Crops"),
         ["class", "Land Type",  "peat_area_ha", "total_area_ha"]]
    .rename(columns={
        "peat_area_ha": "crop_area_ha",
        "total_area_ha": "peat_class_area_ha"
    })
)

crop_proportions = (
        crop_proportions
        .merge(
            total_peat_areas[["class", "total_area_ha"]].drop_duplicates(),
                on="class",
                how="left"
        )
        .rename(columns={"total_area_ha": "peat_class_area_ha"})
)

crop_proportions = pd.concat(
    [crop_proportions, crops_outside],
    ignore_index=True
)

crop_proportions["pct_of_crops_peat"] = (
    100 *
    crop_proportions["crop_area_ha"] /
    crop_proportions["peat_class_area_ha"]
)

# Check these sum to 100%
crop_check = (
    crop_proportions
    .groupby("class")["pct_of_crops_peat"]
    .sum()
)

print(crop_check) # 93.99%, but this is expected because we dropped about 715ha of parcel with multi_crops, out of a total of 11856ha

crop_proportions.sort_values(by=['crop_area_ha'], ascending=False).to_csv(Path(output_path) / "crops_grown_on_peatland_crops_class_all_lpis_single_crops_no_ards.csv", index=False)