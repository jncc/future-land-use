import json
import argparse
import logging
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')
    
def main(polygonPath: str,
         polygonIdColumn: str,
         layerConfig: str,
         eligibilityOutputPath: str):
    """Helper function to generate a table of eligibility for a set of polygons, where all options are eligible

    Args:
        polygonPath (str): Path to intput polygon file
        polygonIdColumn (str): Name of the ID column in the polygon file
        layerConfig (str): Layer config file path
        eligibilityOutputPath (str): Output table path
    """

    with open(layerConfig) as f:
        config = json.load(f)
        eligibilityLayers = config['eligibility_layers']

    logging.info(f'Found {len(eligibilityLayers.keys())} eligiblity layers in the config file')

    polygons = gpd.read_file(polygonPath)
    polygons.drop_duplicates(subset=polygonIdColumn, keep='first', inplace=True)
    
    df = pd.DataFrame(index=polygons[polygonIdColumn], columns=eligibilityLayers.keys())
    df.index.name = 'id'

    for eligibilityLayer in eligibilityLayers:
        df[eligibilityLayer] = True

    df.to_csv(eligibilityOutputPath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate action scores for a given polygon land parcel")
    parser.add_argument('-i', '--poly_source', type=str, required=True, help="Unique ID for the polygon")
    parser.add_argument('-c', '--polygon_id_column', type=str, required=False, default="NGC", help="Column name for the polygon ID")
    parser.add_argument('-l', '--layer_config', type=str, required=False, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-o', '--eligibility_output', type=str, required=False, default="eligibility.csv", help="Output file for eligibility table")

    args = parser.parse_args()

    main(
        args.poly_source, 
        args.polygon_id_column, 
        args.layer_config,
        args.eligibility_output
    )