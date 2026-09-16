# Script to perform geoprocessing for the BALUNNI cost-benefit analysis work

import geopandas as gpd
import shapely as shp
import pandas as pd
from pathlib import Path
from balunni_functions import processPeatData, check_xyz_coordinate_structure, stitchXYZTiles, parcelBatchCreation

# Define inputs folder
input_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\"
output_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Test Peatland Extraction\\Inputs\\"
dtm_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\OSNI_10M_DTM\\"

# Read in datasets
jhi_peatland = gpd.read_file(Path(input_path) / "Peatland\\Peatland.gpkg")
bgs_peatland = gpd.read_file(Path(input_path) / "ni_10k_superficial\\ni_10k_superficial.shp")
peatland_survey = gpd.read_file(Path(input_path) / "peatland_survey\\peatland_survey.shp")
afbi_peatland = gpd.read_file(Path(input_path) / "AFBI_Soil_Series_Map_of_Northern_Ireland\\AFBI_Soil_Series_Map_of_Northern_Ireland.shp")
efs_peatland = gpd.read_file(Path(input_path) / "JNCC Priority Habitats April2026 v2\\JNCC_PriorityHabs_EFS.gpkg", layer="NIEA_Priority_Peatland_Tranche10_V1_1")
lpis_fields = gpd.read_parquet(Path(input_path) / "Nutrient Loading per field\\jncc_2024_extract.parquet")

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
parcelBatchCreation(lpis_fields, 50000, "ID", 29902, output_path)

