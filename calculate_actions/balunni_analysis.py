import geopandas as gpd
import shapely as shp
import pandas as pd
from pathlib import Path
from balunni_functions import stitchoutputs

output_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Test Peatland Extraction\\Outputs\\"
data_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\"
local_path = "C:\\Users\\Rory.Barber\\OneDrive - Joint Nature Conservation Committee\\Documents\\Data for Processing on C\\BALLUNI InVEST Runs\\CBA Data\\"

# Stitch priority data together 
peatland_stitch = stitchoutputs(Path(output_path), Path(output_path), search_text="peatland_50k", file_pattern= "*.csv")
elevation_stitch = stitchoutputs(Path(output_path), Path(output_path), id_column= "id", search_text="elevation_50k", file_pattern= "*.csv")

# Read in stocking data from DSD
stocking_data = gpd.read_parquet(Path(data_path) / "Nutrient Loading per field\\jncc_2024_extract.parquet")
stocking_data['field_id_code'] # This is the unique field id

# Read in LFA data 
lfa_data = pd.read_csv(Path(data_path)/ "LPIS_Fields\\2024_field_data_extract.csv")

# Join datasets up
stocking_peatland = peatland_stitch.join(stocking_data.set_index("field_id_code"), on="parcel_id").join(lfa_data.set_index("FieldNo"), on="parcel_id")

# Get relevant columns to subset data
peatland_cols = [
    'parcel_id',
    'layer',
    'class',
    'percent',
    'field_mea_ha',
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

# Extract rows corresponding to JHI_peatland with 100% class coverage and subset columns using lists above
clean_stocking_peatland = stocking_peatland.loc[(stocking_peatland["layer"] == "JHI_Peatland") & (stocking_peatland["percent"] >= 100), peatland_cols + headcount_cols.tolist() + lfa_cols.tolist()]

# Check that no parcel IDs appear twice for calculations
duplicate_check = clean_stocking_peatland["parcel_id"].duplicated()
duplicate_check

# Get counts of parcels used in calculations for sample size stats
class_counts = (
    clean_stocking_peatland
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
    clean_stocking_peatland
    .groupby(["class", "Land Type"])[headcount_cols.tolist()]
    .sum()
)

area_totals = (
    clean_stocking_peatland
    .groupby(["class", "Land Type"])["field_mea_ha"]
    .sum()
)

# Divide each livestock total by total area
averages = livestock_totals.div(area_totals, axis=0)

print(averages)

averages.to_csv(Path(output_path) / "peatland_land_type_avg_stocking_densities_NI.csv")

# Get proportion of peatland classes in each land classification type
# Get total area of each land classification from parcel data, making sure each parcel is only chosen once 
total_classification_areas = (
    stocking_peatland
    .groupby(["parcel_id", "Land Type"])["field_mea_ha"]
    .sum()
)