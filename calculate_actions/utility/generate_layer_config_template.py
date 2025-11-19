import json
import argparse
import logging
import pandas as pd
import numpy as np
import re
from pathlib import PureWindowsPath, Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

def getPath(vector: bool, vectorPath: str, raster: bool, rasterPath: str, replaceBasePath: str = None, preferRaster: bool = True):
    if vector and raster:
        if preferRaster:
            return getFinalPath(rasterPath, replaceBasePath)
        return getFinalPath(vectorPath, replaceBasePath)

    if vector:
        return getFinalPath(vectorPath, replaceBasePath)
    
    if raster:
        return getFinalPath(rasterPath, replaceBasePath)

def getFinalPath(path: str, replaceBasePath: str = None):
    if replaceBasePath:
        return f'{Path(replaceBasePath).joinpath(PureWindowsPath(path).name)}'
    return f'{Path(path)}'

def filterInputCSV(df: pd.DataFrame, nullTextValues = ['Under development', 'TBD - May merge with above'], filePathColumnName = 'placeholder_file_path', rasterFilePathColumnName = 'raster_filepath_if_applicable'):
    df['vector'] = df[filePathColumnName].notnull() & ~df[filePathColumnName].isin(nullTextValues)
    df['raster'] = df[rasterFilePathColumnName].notnull()
    df.drop(df[~df['vector'] & ~df['raster']].index, inplace=True)

    return df

def main(priorityInputPath: str,
         eligibilityInputPath: str,
         eligibilityInputIsPrecalculated: bool,
         output: str,
         priorityBasePath: str = None,
         eligibilityBasePath:str = None,
         preferRaster: bool = False):
    """Helper function to generate priority and eligbility layer config files

    Args:
        priorityInputPath (str): Priority Input CSV path
        eligibilityInputPath (str): Eligibilty Input CSV path
        output (str): Output JSON path
    """

    priority = filterInputCSV(pd.read_csv(priorityInputPath))
    priorityConf = {k:{} for k in priority['priority_layer_id'].unique()}
    priority.set_index('priority_layer_id', inplace=True)

    for layer in priorityConf:
        path = Path(getPath(priority.loc[layer]['vector'], priority.loc[layer]['placeholder_file_path'], priority.loc[layer]['raster'], priority.loc[layer]['raster_filepath_if_applicable'], priorityBasePath, preferRaster))
        priorityConf[layer] = {
            'layer_name': priority.loc[layer]['service_indicator'],
            'filepath': f'{path}',
            'type': 'vector' if priority.loc[layer]['vector'] else 'raster'
        }
        
    if eligibilityInputIsPrecalculated:
        logging.info('Eligibility input is precalculated, skipping eligibility layer config generation')
        eligibilityConf = {}

        if (Path(eligibilityInputPath).suffix == '.parquet'):
            df = pd.read_parquet(eligibilityInputPath)
        elif (Path(eligibilityInputPath).suffix == '.csv'):
            df = pd.read_csv(eligibilityInputPath)
        else:
            raise ValueError('Precalculated eligibility input must be a parquet or CSV file at preset')

        filter = re.compile(r'^Eligibility_.*$')
        options = [opt for opt in df.columns.tolist() if filter.match(opt)]        
        for layer in options:
            eligibilityConf[layer] = {
                'layer_name': layer.replace('Eligibility_', ''),
                'description': f'Precalculated eligibility layer for {layer}, no file path applicable',
            }

    else:
        logging.info('Generating eligibility layer config')
        eligibility = filterInputCSV(pd.read_csv(eligibilityInputPath))
        eligibilityConf = {k:{} for k in eligibility['eligibility_layer_id'].unique()}
        eligibility.set_index('eligibility_layer_id', inplace=True)

        for layer in eligibilityConf:
            eligibilityConf[layer] = {
                'layer_name': eligibility.loc[layer]['option_code'],
                'filepath': getPath(eligibility.loc[layer]['vector'], eligibility.loc[layer]['placeholder_file_path'], eligibility.loc[layer]['raster'], eligibility.loc[layer]['raster_filepath_if_applicable'], eligibilityBasePath, preferRaster)
            }
    
    outputConfig = {
        'priority_layers': priorityConf,
        'eligibility_layers': eligibilityConf
    }

    with open(output, 'w') as o:
        json.dump(outputConfig, o, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate action scores for a given polygon land parcel")
    parser.add_argument('-p', '--priority-input', type=str, required=True, help="Input CSV file for priority layer config")
    parser.add_argument('-e', '--eligibility-input', type=str, required=True, help="Input CSV file for eligibility config")
    parser.add_argument('--eligibility-input-is-precalculated', type=bool, required=False, help='Flag indicating eligibility input is precalculated rather than direct files', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-o', '--output', type=str, required=True, help='Path to write output to')
    parser.add_argument('--priority-base-path', type=str, required=False, default=None, help='base path to replace found priority paths')
    parser.add_argument('--eligibility-base-path', type=str, required=False, default=None, help='base path to replace found eligibility paths')
    parser.add_argument('--prefer-raster', type=bool, default=False, action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    main(
        args.priority_input,
        args.eligibility_input,
        args.eligibility_input_is_precalculated,
        args.output,
        args.priority_base_path,
        args.eligibility_base_path,
        args.prefer_raster
    )