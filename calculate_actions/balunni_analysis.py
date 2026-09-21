import geopandas as gpd
import numpy as np
import shapely as shp
import pandas as pd
import rasterio
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

# Read in peatland and elevation data
jhi_peat = gpd.read_file(Path(input_path) / "JHI_Peatland_Processed.gpkg")
with rasterio.open("O:\\EAT\\EOMonitoringApplications\\NorthernIreland2022\\Topography\\outputs\\NI_DTM_10m_TM65_2023_merged.tif") as src:
    dem = src.read(1)
    transform = src.transform
    nodata = src.nodata

## STEP 1: Stitch priority data outputs together if needed using pre-defined function
#peatland_stitch = stitchoutputs(Path(extraction_path), Path(extraction_path), search_text="peatland_50k", file_pattern= "*.csv")
#elevation_stitch = stitchoutputs(Path(extraction_path), Path(extraction_path), id_column= "id", search_text="elevation_50k", file_pattern= "*.csv")
peatland_stitch = pd.read_csv(Path(extraction_path)/ "peatland_50k_combined.csv")

## STEP 2: Calculate the average stocking density of each livestock category on each combination of peatland and land classification
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

print(stocking_data["geometry_area_diff"].describe()) # identical, suggest using geometry_area moving forward in other calculations

# Join datasets up 
stocking_peatland = peatland_stitch.join(stocking_data.set_index("field_id_code"), on="parcel_id").join(lfa_data.set_index("FieldNo"), on="parcel_id")

# Count number of parcels retained and make sure IDs matches original stocking_data, should be equal
peatland_ids = set(stocking_peatland["parcel_id"].dropna())
stocking_ids = set(stocking_data["field_id_code"].dropna())

if peatland_ids != stocking_ids:
    print("Error - parcel IDs do not match between datasets")

    missing_from_peatland = stocking_ids - peatland_ids
    missing_from_stocking = peatland_ids - stocking_ids

    print(f"Missing from peatland: {len(missing_from_peatland)}") # One parcel missing which is a tiny island in an estuary - none of the peatland datasets overlap and no reported livestock so ignoring
    print(f"Missing from stocking: {len(missing_from_stocking)}")

# Check area columns are still intact - both should return nothing
mea_nas = stocking_peatland["field_mea_ha"].isna().sum()
field_nas = stocking_peatland["geometry_area"].isna().sum()

# Get relevant columns to subset data
peatland_cols = [
    'parcel_id',
    'layer',
    'class',
    'percent',
    'geometry_area',
    'field_mea_ha'
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
clean_stocking_peatland_100_pct = clean_stocking_peatland.loc[(clean_stocking_peatland["percent"] >= 100)]

# Check that no parcel IDs appear twice for calculations - some do because of different business codes in LFA data etc. This is fine but we need to make sure the headcount/area is only considered once for each parcel
duplicate_check = clean_stocking_peatland_100_pct["parcel_id"].duplicated(keep="first")
print(clean_stocking_peatland_100_pct.loc[duplicate_check])
clean_stocking_peatland_100_pct.drop_duplicates("parcel_id", inplace=True) # Retain only one parcel for stocking density calculations

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
    clean_stocking_peatland_100_pct
    .groupby("class")["Land Type"]
    .value_counts()
    .reset_index()
)

class_counts.columns = ["class", "Land Type", "count"]

# Write out
class_counts.to_csv(Path(output_path) / "peatland_land_type_sample_sizes_NI.csv")

# Now calculate the  stocking density per hectare
# Sum livestock counts and area by class
livestock_totals = (
    clean_stocking_peatland_100_pct
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .sum()
)

# Check which area total we want first before doing calculations. Assume field_mea?
area_totals = (
    clean_stocking_peatland_100_pct
    .groupby(["class", "Land Type"])["field_mea_ha"]
    .sum()
)

# Divide each livestock total by total area
densities = livestock_totals.div(area_totals, axis=0)

print(densities)

densities.to_csv(Path(output_path) / "peatland_land_type_stocking_densities_NI.csv")

# Alternative approach - calculate stocking density on each of the parcels and then take the average of these 
density_df = clean_stocking_peatland_100_pct.copy()

for livestock in headcount_cols:
    density_df[livestock] = (
        density_df[livestock] /
        density_df["field_mea_ha"]
    )

averages = (
    density_df
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .mean()
)

print(averages)

averages.to_csv(Path(output_path) / "peatland_land_type_avg_parcel_stocking_densities_NI.csv")

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

# write out binary raster generated earlier to check this was done appropriately in QGIS - O:\EAT\Ecosystems Analysis\BALLUNI\CBA Analysis\Upland_Data_Check.qgz
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

# Calculate raster stats, mean in this case will be the proportion of pixels in a parcel above the threshold
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
#summary_upland.to_csv(Path(output_path) / "peatland_upland_areas_NI.csv", index=False)
summary_upland = pd.read_csv(Path(output_path) / "peatland_upland_areas_NI.csv")

## STEP 4: Get proportion of peatland classes in each land classification type
# We already have a summary output for peatland classes above/below upland threshold with total area of each class in ha - summary_upland
# So just need to work out the proportion of this total area that overlaps with different land classifications. Add a column to the data to get area of each peat class
clean_stocking_peatland["peat_area_ha"] = (
    (clean_stocking_peatland["percent"] / 100) * clean_stocking_peatland["geometry_area"] # use geometry area as looking at overall proportions not claimed areas
)

# Get total area of each land classification from parcel data, for each peatland class x land type combo
peat_classification_areas = (
    clean_stocking_peatland
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
total_peat_areas.sort_values(by=['class']).to_csv(Path(output_path) / "peatland_land_type_area_proportions.csv", index=False)

## STEP 5: Calculate the percentages of different crop types grown on cropland class in the JHI data 
# We have the total area of Crops class from summary_upland 
clean_cropland_peat = clean_stocking_peatland.loc[(clean_stocking_peatland["class"] == "Crops")]

# Some parcels have multiple crops being grown on them, inspect these to identify values to remove from proportion estimates
multi_crops = clean_cropland_peat["parcel_id"].duplicated(keep=False)
print(clean_cropland_peat.loc[(multi_crops)]) # so UsageCode is the key column containing info, 

# Problem we have is that the peatland area is not necessarily 100% of the parcel, 
# where we have multiple crops we don't know how this aligns with the peatland coverage
# so we actually need to only include those with 100% coverage (much smaller sample) or just remove those where multiple crops are recorded (~2% parcels). Suggest the latter

clean_single_cropland_peat = clean_cropland_peat.drop_duplicates(subset="parcel_id", keep=False)

# Group by UsageCode and sum peat_area_ha, then merge with total areas of each class above to get total area of Crops class, pulling over area outside parcel data
crop_proportions = (
    clean_cropland_peat
    .groupby(["class","UsageCode"], as_index=False)["peat_area_ha"]
    .sum()
    .rename(columns={"peat_area_ha": "crop_area_ha"})
)

crops_outside = (
    total_peat_areas
    .loc[(total_peat_areas["Land Type"] == "Outside parcel boundary") & (total_peat_areas["class"] == "Crops"),
         ["class", "Land Type",  "peat_area_ha", "total_area_ha"]]
    .rename(columns={
        "peat_area_ha": "crop_area_ha",
        "total_area_ha": "peat_class_area_ha",
        "Land Type": "UsageCode"
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

print(crop_check) # 99.99%, but this is expected because we dropped about 2% of parcels earlier on with multiple crop types. 

crop_proportions.sort_values(by=['crop_area_ha'], ascending=False).to_csv(Path(output_path) / "crops_grown_on_peatland_crops_class.csv", index=False)