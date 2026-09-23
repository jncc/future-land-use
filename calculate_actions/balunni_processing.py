# Script to perform geoprocessing for the BALUNNI cost-benefit analysis work

import geopandas as gpd
import shapely as shp
import pandas as pd
import pyogrio
from pathlib import Path
from balunni_functions import processPeatData, check_xyz_coordinate_structure, stitchXYZTiles, parcelBatchCreation

# Define inputs folder
input_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\"
output_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Final Peatland Extraction\\Inputs\\"
dtm_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\OSNI_10M_DTM\\"

# Read in datasets
jhi_peatland = gpd.read_file(Path(input_path) / "Peatland\\Peatland.gpkg")
bgs_peatland = gpd.read_file(Path(input_path) / "ni_10k_superficial\\ni_10k_superficial.shp")
peatland_survey = gpd.read_file(Path(input_path) / "peatland_survey\\peatland_survey.shp")
afbi_peatland = gpd.read_file(Path(input_path) / "AFBI_Soil_Series_Map_of_Northern_Ireland\\AFBI_Soil_Series_Map_of_Northern_Ireland.shp")
efs_peatland = gpd.read_file(Path(input_path) / "JNCC Priority Habitats April2026 v2\\JNCC_PriorityHabs_EFS.gpkg", layer="NIEA_Priority_Peatland_Tranche10_V1_1")
stocking_fields = gpd.read_parquet(Path(input_path) / "Nutrient Loading per field\\jncc_2024_extract.parquet")
lfa_fields = pd.read_csv(Path(input_path)/ "LPIS_Fields\\2024_field_data_extract.csv")
lpis_fields = gpd.read_file(Path(input_path) / "LPIS_Fields\\LPIS_Fields.gpkg", layer="Fields_2024")

# Process peatland datasets for extraction step
processPeatData(jhi_peatland, 29902, "Class", output_path, "JHI_Peatland_Processed.gpkg")
processPeatData(bgs_peatland, 29902, "LEX", output_path, "BGS_Peatland_Processed.gpkg")
processPeatData(peatland_survey, 29902, "CLASS", output_path, "Peatland_Survey_Processed.gpkg")
processPeatData(jhi_peatland, 29902, "Series", output_path, "AFBI_Peatland_Processed.gpkg")
processPeatData(efs_peatland, 29902, "CLASS", output_path, "EFS_Peatland_Processed.gpkg")

# Stitch together 10m DTM
dtm_sheets_checked = check_xyz_coordinate_structure(Path(dtm_path), 10, 5)
stitchXYZTiles(Path(dtm_path), Path(dtm_path) / "OSNI_10m_DTM.tif", 29902, 10)

with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    print(dtm_sheets_checked)

# Batch up land parcels into smaller chunks for processing
parcelBatchCreation(stocking_fields, 50000, "ID", 29902, output_path)

## ADDITIONAL PROCESSING DONE FOLLOWING DECISION TO ALSO CHECK PEATLAND OVERLAPS WITH LPIS FIELDS CONTAINING NO LIVESTOCK - 22/09/26
# This uses "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Outputs\\LPIS_Fields_no_stocking.csv" to filter the LPIS field data gpkg, not the Geoparquet containing livestock data from DSD
# This subset of parcels is then run through the extraction process again before being analysed back in the balunni_anlaysis.py script. 

# Subset lfa dataset to get those missing from the stocking dataset - Need to do this for the raw parcel dataset itself? But we want the LFA designation so probably best to include his already
lfa_not_in_stocking = (lfa_fields.loc[
    ~lfa_fields["FieldNo"].isin(stocking_fields["field_id_code"])
].drop_duplicates(subset=["FieldNo"]))
print(lfa_not_in_stocking)
print(lfa_not_in_stocking["MEAArea"].sum()) # 61k ha from 42k parcels not in the stocking data
#lfa_not_in_stocking.to_csv((Path(output_path) / "LPIS_Fields_no_stocking.csv")) # This data is then used to re-process LPIS fields for peatland classification outside of stocking areas

# Create set of IDs to filter field gpkg
missing_fieldnos = set(
    lfa_not_in_stocking["FieldNo"]
)
print(f"Missing FieldNos: {len(missing_fieldnos):,}") #42,283 parcels in LFA classification not in stocking data

parcels_subset = lpis_fields.loc[
    lpis_fields["ID"].isin(missing_fieldnos)
]

print(f"Missing parcels: {len(parcels_subset):,}") #38,666 parcels in actual geometry dataset, so several thousand missing geometry data from LFA, not much we can do

# Create a parcel batch which is cleaner and trimmed down to essential columns
parcelBatchCreation(parcels_subset, 50000, "ID", 29902, Path(output_path) /"Non-stocking Parcels\\")
