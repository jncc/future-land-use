
import argparse
import json
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

def main(input: str, name: str, outputPath: str = None):
    outputs = {}

    aggregation = pd.read_csv(input, index_col='option')
    outputs[name] = {
       'operation': 'MAX',
       'options': {}
    }
    for option in sorted(aggregation.index):
        outputs[name]['options'][option] = list(aggregation.loc[option][aggregation.loc[option].values].index)

    print(outputs)

    if outputPath:
        with open(outputPath, 'w') as o:
            json.dump(outputs, o)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate QEIA matrix config file")
    parser.add_argument('-a', '--aggregation_config', type=str, required=True, help='column aggregation CSV')
    parser.add_argument('-n', '--aggregation_name', type=str, required=True, help='Name of the aggregation to generate')
    parser.add_argument('-o', '--output_path', type=str, required=False, default=None, help="Output file for aggregation JSON")

    args = parser.parse_args()

    main(
        args.aggregation_config,
        args.aggregation_name,
        args.output_path
    )
