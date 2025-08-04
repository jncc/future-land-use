import json
import argparse
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')
    
def main(layerConfig: str,
         output: str,
         minRange: float = -3,
         maxRange: float = 3,
         wholeNumbers: bool = True):
    """Generate a random QEIA matrix config file with specified range for impact scores

    Args:
        layerConfig (str): Input layer config file path for JSON input
        output (str): Output JSON file path
    """
    with open(layerConfig) as f:
        layers = json.load(f)

    qeia = {k:{} for k in layers['eligibility_layers']}
    for layer in qeia.keys():
        for priority in layers['priority_layers'].keys():
            if wholeNumbers:
                qeia[layer][priority] = np.random.randint(minRange, maxRange + 1)
            else:
                qeia[layer][priority] = np.random.uniform(minRange, maxRange)

    with open(output, 'w') as o:
        json.dump(qeia, o)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a random QEIA matrix config file")
    parser.add_argument('-l', '--layer_config', type=str, required=True, help='Layer config with valid layers to export against')
    parser.add_argument('-o', '--qeia_output', type=str, required=False, default="qeia.json", help="Output file for qeia JSON")
    parser.add_argument('--min_range', type=float, default=-3, help='Minimum range for impact scores')
    parser.add_argument('--max_range', type=float, default=3, help='Maximum range for impact scores')
    parser.add_argument('--whole_numbers', action='store_true', help='Generate whole numbers for impact scores')
    
    args = parser.parse_args()

    main(
        args.layer_config,
        args.qeia_output,
        minRange=args.min_range,
        maxRange=args.max_range,
        wholeNumbers=args.whole_numbers
    )
