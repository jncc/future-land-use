# Script to perform geoprocessing for the BALUNNI cost-benefit analysis work

import geopandas as gpd
import shapely as shp
from pathlib import Path
from balunni_functions import processPeatData, stitchXYZTiles

# Define inputs folder
inputpath = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\"
outputpath = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\CBA Analysis\\Test Peatland Extraction\\Inputs\\"
dtm_path = "O:\\EAT\\Ecosystems Analysis\\BALLUNI\\Data\\OSNI_10M_DTM\\"

# Read in datasets
jhi_peatland = gpd.read_file(Path(inputpath) / "Peatland\\Peatland.gpkg")
bgs_peatland = gpd.read_file(Path(inputpath) / "ni_10k_superficial\\ni_10k_superficial.shp")
peatland_survey = gpd.read_file(Path(inputpath) / "peatland_survey\\peatland_survey.shp")
afbi_peatland = gpd.read_file(Path(inputpath) / "AFBI_Soil_Series_Map_of_Northern_Ireland\\AFBI_Soil_Series_Map_of_Northern_Ireland.shp")
efs_peatland = gpd.read_file(Path(inputpath) / "JNCC Priority Habitats April2026 v2\\JNCC_PriorityHabs_EFS.gpkg", layer="NIEA_Priority_Peatland_Tranche10_V1_1")
lpis_fields = gpd.read_file()

# Process peatland datasets for extraction step
processPeatData(jhi_peatland, 29902, "Class", outputpath, "JHI_Peatland_Processed.gpkg")
processPeatData(bgs_peatland, 29902, "Class", outputpath, "BGS_Peatland_Processed.gpkg")
processPeatData(peatland_survey, 29902, "Class", outputpath, "Peatland_Survey_Processed.gpkg")
processPeatData(jhi_peatland, 29902, "Class", outputpath, "AFBI_Peatland_Processed.gpkg")
processPeatData(efs_peatland, 29902, "CLASS", outputpath, "EFS_Peatland_Processed.gpkg")

# Stitch together 10m DTM
stitchXYZTiles(Path(dtm_path), Path(dtm_path) / "OSNI_10m_DTM.tif")

