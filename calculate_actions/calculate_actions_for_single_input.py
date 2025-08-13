import json
import argparse
import logging
import shapely

from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from priority_scores import extractPriorityScoresForInputPolygon, calculateWeightedPriorityScores
from eligibility import calculateOptionEligibilityForInputPolygon
from mcda import calculateMCDAForPriorityScoresWithEligibility
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

def main(polyId: str, wkt: str, layerConfig: str, weightingsConfig: str, qeiaMatrix: str, output: str):
    """Process a single polygon through to MCDA, using weighted priority scores,
    eligible option layers and an input QEIA matrix

    Args:
        polyId (str): An ID for this polygon
        wkt (str): A path to a WKT file describing the input polygon as WKT (in the same projection as the eligibility and priority layers)
        layerConfig (str): Path to a JSON file containing a configuration object for layers (priority and eligibility)
        qeiaMatrix (str): Path to a JSON file containing a configuration object for a QEIA matrix to process against
        output (str): Optional path to store MCDA output to as a .csv file
    """
    (totalStartWallTime, totalStartProcessTime) = startTimers()
    logging.info(f'Generating actions for polygon {polyId} defined in {wkt}')

    priorityLayers: dict[str, PriorityLayer] = {}
    eligibilityLayers: dict[str, EligibilityLayer] = {}
    with open(layerConfig) as f:
        config = json.load(f)
        priorityLayers = processPriorityLayers(config['priority_layers'])
        eligibilityLayers = processEligibilityLayers(config['eligibility_layers'])

    logging.info(f'Found {len(priorityLayers)} priority layers in the config file')

    with open(weightingsConfig) as f:
        weightings = json.load(f)
        if not set(weightings.keys()).issuperset(priorityLayers.keys()):
            raise ValueError('Mismatch between priority layers and weightings')

    with open(qeiaMatrix) as f:
        config = json.load(f)
        rawQeia = QEIAMatrix(config)

    logging.info(f'Imported Raw QEIA matrix')

    polygonStr = ''
    with open(wkt) as f:
        polygonStr = f.readline()
        polygon = shapely.from_wkt(geometry=polygonStr)

    logging.info(f'Input polygon: {polygon}')
    
    (procStartWallTime, procStartProcessTime) = startTimers()
    (startWallTime, startProcessTime) = startTimers()

    logging.info('Calculate priority scores')
    priorityScores = extractPriorityScoresForInputPolygon(polyId, polygon, priorityLayers)
    
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
    logging.info('---------------------------- Priority Scores Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')
    print(priorityScores)

    logging.info('Calculating weighted priority scores')
    (startWallTime, startProcessTime) = startTimers()

    weightedPriorityScores = calculateWeightedPriorityScores(priorityScores, weightings)

    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

    logging.info('---------------------------- Weighted Priority Scores Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} milliseconds')
    logging.info(f'Process Time: {processTime} milliseconds')
    print(weightedPriorityScores)

    logging.info('Determining polygon eligibility')
    (startWallTime, startProcessTime) = startTimers()

    optionEligbility = calculateOptionEligibilityForInputPolygon(polyId, polygon, eligibilityLayers)
    
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
    
    logging.info('---------------------------- Eligibility Discovery Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')
    print(optionEligbility)    

    logging.info("Calculate action scores using priorities and filtered QEIA")
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia, optionEligbility)
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

    logging.info('---------------------------- MCDA Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} milliseconds')
    logging.info(f'Process Time: {processTime} milliseconds')
    print(mcda)
    print(mcda.transpose())

    if output:
        mcda.to_csv(output)

    (wallTime, processTime) = endTimers(procStartWallTime, procStartProcessTime, 1)
    logging.info('---------------------------- Processing Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    (wallTime, processTime) = endTimers(totalStartWallTime, totalStartProcessTime, 1)
    logging.info('---------------------------- Execution Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    # save action_scores to file or something?

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate action scores for a given polygon land parcel")
    parser.add_argument('-i', '--poly_id', type=str, required=True, help="Unique ID for the polygon")
    parser.add_argument('-p', '--polygon_wkt', type=str, required=True, help="WKT file containing polygon geometry")
    parser.add_argument('-l', '--layer_config', type=str, required=True, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-w', '--weightings_config', type=str, required=True, default="weightings.json", help="JSON file containing priority weightings")
    parser.add_argument('-q', '--qeia_matrix', type=str, required=True, help="Raw QEIA impact score matrix file")
    parser.add_argument('-o', '--output', type=str, required=False, help="Optional filepath to store output MCDA data as a .csv file")

    args = parser.parse_args()

    main(args.poly_id, args.polygon_wkt, args.layer_config, args.weightings_config, args.qeia_matrix, args.output)