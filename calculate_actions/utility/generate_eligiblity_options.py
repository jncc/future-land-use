from common.layers import EligibilityLayer, processEligibilityLayers
from eligibility import calculateOptionEligibilityForInputPolygons
from pathlib import Path
import logging
import argparse
import json


def main(polygonPath: str,
         polygonIdColumn: str,
         layerConfig: str,
         eligibilityOptionsPath: str,
         overwriteEligibilityOptions: bool):
    
    logging.info('Determining polygon eligibility')

    config = json.load(open(layerConfig))

    if Path(eligibilityOptionsPath).exists():
        if overwriteEligibilityOptions:
            logging.warning(f'Output path {eligibilityOptionsPath} already exists, overwriting')
        else:
            raise FileExistsError(f'Output path {eligibilityOptionsPath} already exists, use --overwrite-eligibility-options to overwrite')

    logging.info('Processing eligibility layers')

    eligibilityLayers: dict[str, EligibilityLayer] = {}
    eligibilityLayers = processEligibilityLayers(config['eligibility_layers'])

    optionEligbility = calculateOptionEligibilityForInputPolygons(Path(polygonPath), polygonIdColumn, eligibilityLayers)
    optionEligbility.to_csv(eligibilityOptionsPath, index=True, index_label='id')
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate eligibility options for a set of input polygons using eligibility layers')
    parser.add_argument('-i', '--polygon-source', type=str, required=True, help='Path to the input polygon file')
    parser.add_argument('-c', '--polygon-id-column', type=str, required=False, default='id_parcel', help='Column name for the polygon ID')
    parser.add_argument('-l', '--layer-config', type=str, required=False, help='JSON file containing eligibility layers')
    parser.add_argument('-o', '--eligibility-options-path', type=str, required=False, help='Path to output eligibility options file')
    parser.add_argument('--overwrite-eligibility-options', required=False, help='Overwrite existing eligibility options file if it exists', default=False, action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    main(
        args.polygon_source, 
        args.polygon_id_column, 
        args.layer_config,
        args.eligibility_options_path,
        args.overwrite_eligibility_options
    )
