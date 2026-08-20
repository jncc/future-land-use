import geopandas as gpd
import shapely as shp
from pathlib import Path

# Define function to read in process peatland datasets
def processPeatData(dataset: gpd.GeoDataFrame, targetcrs: int, classcolumn: str, outpath: Path | None = None, filename: str | None = None) -> gpd.GeoDataFrame:
    """This function takes a dataset, checks it is in the target crs and reprojects it if needed. It then
        polygonizes any multipolygons and generates spatial indexes if not already present before writing out.

        Args:
            dataset (GeoDataFrame) : A GeoPandas dataframe loaded into the script (e.g. a peatland dataset)
            targetcrs (int) : The target CRS that the data should already be in, if not it will be reprojected to this CRS. Entered as EPSG code
            classcolumn (str): A string defining the name of the classcolumn, to retain in the final output.
            outpath (Path, optional): An output path for writing the dataset too
            filename (str, optional): Output filename to write to
            
        Returns:
            gpd.GeoDataframe: A GeoPandas dataframe containing the processed dataset for use in the extraction workflow
    """

    # Check dataset is in appropriate structure and correct if needed
    if dataset.geometry.name != "geometry":
        dataset = dataset.rename_geometry("geometry")
        print('Changed geometry column name to geometry')

    if dataset.crs is None:
        raise ValueError("Dataset has no CRS defined")

    if dataset.crs != targetcrs:
        dataset = dataset.to_crs(targetcrs)
        print(f"Reprojecting dataset from"
              f"{dataset.crs} to {targetcrs}")


    # Polygonise if 
    if (dataset.geom_type == "MultiPolygon").any():
        dataset = dataset.explode(index_parts=False).reset_index(drop=True)

    # Trim down dataset to essential columnns
    if classcolumn not in dataset.columns:  
        raise ValueError(f"Column '{classcolumn}' not found in dataset")
    
    dataset = dataset[[classcolumn, "geometry"]]

    # Write out

    if outpath is not None and filename is not None:
        fullpath = Path(outpath) / filename
        dataset.to_file(fullpath, driver="GPKG")
        
    return dataset