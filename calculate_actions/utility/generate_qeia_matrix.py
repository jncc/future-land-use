import json
import argparse
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')
    
def main(input: str,
         output: str,
         layerConfig: str):
    """Helper function to generate a QEIA config json file from a csv input

    Args:
        input (str): Input CSV file path
        output (str): Output JSON file path
    """
    with open(layerConfig) as f:
        layers = json.load(f)

    with open(input) as f:
        qeia_input = pd.read_csv(input)
        qeia_input.dropna(subset=['eligibility_layer_id'], inplace=True)
        qeia_input.replace({np.nan: None}, inplace=True)    
    
    # if not set(qeia_input['eligibility_layer_id'].unique()).issuperset(set(layers['eligibility_layers'].keys())):
    #     raise ValueError('Input QEIA CSV does not contain all required Eligiblity layers')

    qeia = {k:{} for k in layers['eligibility_layers']}
    for i, row in qeia_input[qeia_input['eligibility_layer_id'].isin(layers['eligibility_layers'].keys())].iterrows():
        if row['priority_layer_id'] in layers['priority_layers'].keys():
            qeia[row['eligibility_layer_id']][row['priority_layer_id']] = row['impact_score']

    with open(output, 'w') as o:
        json.dump(qeia, o)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate QEIA matrix config file")
    parser.add_argument('-i', '--qeia_input', type=str, required=True, help='input qeia csv')
    parser.add_argument('-o', '--qeia_output', type=str, required=False, default="qeia.json", help="Output file for qeia JSON")
    parser.add_argument('-l', '--layer_config', type=str, required=True, help='Layer config with valid layers to export against')

    args = parser.parse_args()

    main(
        args.qeia_input,
        args.qeia_output,
        args.layer_config
    )
