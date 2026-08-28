import geopandas as gpd
import shapely as shp
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from pyproj import CRS

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

def stitchXYZTiles(input_folder: Path, output_raster: Path, crs: int | str, res: int):
    """
    This function takes an input folder containing a set of txt files representing elevation at various locations
    It works out the overall size of the output raster, creates a blank one and then reads each txt files in to populates the raster
    
    Args:
        input_folder (Path): An input folder path containing all the relevant txt files
        output_raster (Path): An output filepath for writing the raster to
        crs (int | str): An string with the CRS (format "EPSG: 29902") or simply the integer code
        res (int): An integer containing the resolution of the input txt files and the output raster
        
    Returns:
        output_raster (Path): An output filepath where the raster is written to
    """

    if isinstance(crs, int):
        crs = f"EPSG:{crs}"

    files = list(input_folder.glob("Sheet*.txt"))

    if len(files) == 0:
        raise ValueError("No files found")

    print(f"Found {len(files)} files")

    xmin = np.inf
    xmax = -np.inf
    ymin = np.inf
    ymax = -np.inf

    # First pass - determine extent
    for file in files:

        df = pd.read_csv(
            file,
            sep=r"\s+",
            header=None,
            names=["x", "y", "z"]
        )

        xmin = min(xmin, df.x.min())
        xmax = max(xmax, df.x.max())

        ymin = min(ymin, df.y.min())
        ymax = max(ymax, df.y.max())

    resolution = res

    width = int(round((xmax - xmin) / resolution)) + 1
    height = int(round((ymax - ymin) / resolution)) + 1

    print(f"Output raster size: {width:,} x {height:,}")

    raster = np.full(
        (height, width),
        -9999,
        dtype=np.float32
    )

    # Second pass - populate raster
    for i, file in enumerate(files, start=1):

        print(f"{i}/{len(files)}: {file.name}")

        df = pd.read_csv(
            file,
            sep=r"\s+",
            header=None,
            names=["x", "y", "z"]
        )

        cols = (
            (df["x"] - xmin) / resolution
        ).round().astype(int)

        rows = (
            (ymax - df["y"]) / resolution
        ).round().astype(int)

        raster[rows, cols] = df["z"].values

    transform = from_origin(
        xmin,
        ymax,
        resolution,
        resolution
    )

    with rasterio.open(
        output_raster,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype=np.float32,
        crs=crs,
        nodata=-9999,
        transform=transform
    ) as dst:

        dst.write(raster, 1)

    print("Finished")

    return(output_raster)

def parcelBatchCreation(input_parcels: gpd.GeoDataFrame, chunksize: int, id_column:str, targetcrs: int | str, output_path: Path):
    """
    This function takes an input parcel dataset and divides it up into more manageable batches for processing
    It splits it up into user-defined chunks and writes these out to the output path. 
    
    Args:
        input_parcels (Path): An input parcel file to be divided up into smaller batches
        chunksize (int): Number of parcels to be contained in each file
        id_column (str): A column name containing a unique id for each row (parcel) in the dataset
        targetcrs (int | str): Either integer EPSG code or string 
        output_path (Path): An output filepath for writing the parcel batches to
   
    Returns:
        list[Path]: Paths of written batch files.
    """
    # Check dataset is in appropriate structure and correct if needed
    if input_parcels.geometry.name != "geometry":
        input_parcels = input_parcels.rename_geometry("geometry")
        print('Changed geometry column name to geometry')

    if input_parcels.crs is None:
        raise ValueError("Dataset has no CRS defined")

    targetcrs = CRS.from_user_input(targetcrs)

    if input_parcels.crs != targetcrs:
        original_crs = input_parcels.crs
        input_parcels = input_parcels.to_crs(targetcrs)
        print(f"Reprojecting dataset from {original_crs} to {targetcrs}")


    # Polygonise if needed
    if (input_parcels.geom_type == "MultiPolygon").any():
        input_parcels = input_parcels.explode(index_parts=False).reset_index(drop=True)

    # Trim down dataset to essential columnns
    if id_column not in input_parcels.columns:  
        raise ValueError(f"Column '{id_column}' not found in dataset")
    
    input_parcels = input_parcels[[id_column, "geometry"]]

    # Subset dataset into different files using the defined chunksize, take note of file_number
    # Create output directory   
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Split into batches and write out 
    written_files = []

    for batch_number, start_row in enumerate(
        range(0, len(input_parcels), chunksize),
        start=1
    ):
        batch = input_parcels.iloc[start_row:start_row + chunksize]

        filename = f"parcel_batch_{batch_number:03d}.gpkg"
        fullpath = output_path / filename

        batch.to_file(fullpath, driver="GPKG")

        written_files.append(fullpath)
    print(
    f"Wrote batch {batch_number} "
    f"({len(batch)} parcels) to {fullpath}"
    )

    return written_files