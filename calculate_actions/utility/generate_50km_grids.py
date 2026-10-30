import argparse
import logging
import geopandas as gpd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')
logging.getLogger('pyogrio._io').setLevel(logging.WARNING)
    
def main(input: str,
         outputPath: str,
         osbngGrid: str,
         prefix: str):
    """Helper function to grid an input parquet to 50 km square geopackages

    Args:
        input (str): Input parquet file path
        outputPath (str): Output folder path
        osbngGrid (str): Ordnance Survey British National Grids geopackage
        prefix (str): Prefix for output geopackage filenames
    """
    
    # Input polygons
    gdf = gpd.read_parquet(input)

    # 50 km grid polygons
    grid = gpd.read_file(osbngGrid, layer="osbng_grid_50km")

    # Ensure input polygons have the same CRS as the grid
    if not gdf.crs.equals(grid.crs):
        gdf = gdf.to_crs(grid.crs)

    # Group polygons by the grid they fall into, keeping original columns from input file
    # Each parcel is assigned to exactly one grid square (via a point guaranteed to lie inside it) so parcels
    # crossing a grid boundary are not duplicated across outputs
    points = gpd.GeoDataFrame(geometry=gdf.representative_point(), crs=gdf.crs)
    joined = gpd.sjoin(points, grid[["bng_ref", "geometry"]], how="left", predicate="intersects")
    
    # A point on a shared grid edge matches both squares, keep the first so each parcel is only written once
    joined = joined[~joined.index.duplicated(keep="first")]
    gdf["bng_ref"] = joined["bng_ref"]

    unassigned = gdf["bng_ref"].isna().sum()
    if unassigned:
        logging.warning(f"{unassigned} parcels did not fall in any grid square and will not be written")

    outdir = Path(outputPath)
    outdir.mkdir(exist_ok=True)

    # Write out to output folder
    total = 0
    for bng_ref, tile in gdf.groupby("bng_ref"):
        name = f"{prefix}_{bng_ref}"
        tile.drop(columns="bng_ref").to_file(outdir / f"{name}.gpkg", layer=name, driver="GPKG")
        total += len(tile)
        logging.info(f"{name}: {len(tile)} parcels")

    logging.info(f"Wrote {total} of {len(gdf)} parcels to {outdir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Grid an input parquet to 50 km square geopackages")
    parser.add_argument('-i', '--input', type=str, required=True, help='input parquet file')
    parser.add_argument('-o', '--output', type=str, required=False, default="output", help="Output folder for geopackages")
    parser.add_argument('-g', '--osbng_grids', type=str, required=True, help='Ordnance Survey British National Grids geopackage')
    parser.add_argument('--prefix', type=str, required=False, default="rpa_parcels", help="Prefix for output geopackage filenames")

    args = parser.parse_args()

    main(
        args.input,
        args.output,
        args.osbng_grids,
        args.prefix
    )
