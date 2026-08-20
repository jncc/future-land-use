# Script to perform geoprocessing for the BALUNNI cost-benefit analysis work

import geopandas as gpd
import shapely as shp
from pathlib import Path
from balunni_functions import processPeatData

# Define inputs folder
inputpath = "C:\\Users\\Rory.Barber\\Joint Nature Conservation Committee\\Balancing Land Use Needs in NI - Documents\\BALLUNNI Workstreams 26-27\\Land Use Modelling Needs\\Data\\Peatland\\"
outputpath = ""

# Read in datasets
jhi_peatland = gpd.read_file(Path(inputpath) / "Peatland.gpkg")
bgs_peatland = gpd.read_file(Path(inputpath) / "Peatland.gpkg")
peatland_survey = gpd.read_file(Path(inputpath) / "Peatland.gpkg")
afbi_peatland = gpd.read_file(Path(inputpath) / "Peatland.gpkg")

# Process peatland datasets
processPeatData(jhi_peatland, 29902, "Class", outputpath, "JHI_Peatland_Processed.gpkg")
processPeatData(bgs_peatland, 29902, "Class", outputpath, "BGS_Peatland_Processed.gpkg")
processPeatData(peatland_survey, 29902, "Class", outputpath, "Peatland_Survey_Processed.gpkg")
processPeatData(jhi_peatland, 29902, "Class", outputpath, "AFBI_Peatland_Processed.gpkg")