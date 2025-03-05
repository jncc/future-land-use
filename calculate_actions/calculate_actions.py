import json
import argparse
import logging
import shapely

from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from priority_scores import Calculator as PriorityCalculator, Weighting as PriorityWeighting
from eligibility import Calculator as EligibilityCalculator
from mcda import calculateMultiCriteriaDecisionAnalysisForParcel

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

def main(polyId: str, wkt: str, layerConfig: str, qeiaMatrix: str):
    """Process a single polygon through to MCDA, using weighted priority scores,
    eligible option layers and an input QEIA matrix

    Args:
        polyId (str): An ID for this polygon
        wkt (str): A path to a WKT file describing the input polygon as WKT (in the same projection as the eligibility and priority layers)
        layerConfig (str): Path to a JSON file containing a configuration object for layers (priority and eligibility)
        qeiaMatrix (str): Path to a JSON file containing a configuration object for a QEIA matrix to process against
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

    logging.info('Calculate priority scores')
    (startWallTime, startProcessTime) = startTimers()
    
    priorityCalculator = PriorityCalculator(priorityLayers)
    priorityScores = priorityCalculator.calculatePriorityScoreForPolygon(polygon)
    
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
    
    logging.info(priorityScores)
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    logging.info('Calculating weighted priority scores')
    (startWallTime, startProcessTime) = startTimers()

    priorityWeightingCalculator = PriorityWeighting(priorityLayers)
    weightedPriorityScores = priorityWeightingCalculator.calculateWeightings(priorityScores)
    
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

    logging.info(weightedPriorityScores)
    logging.info(f'Wall Time: {wallTime} milliseconds')
    logging.info(f'Process Time: {processTime} milliseconds')

    logging.info('Determining polygon eligibility')
    (startWallTime, startProcessTime) = startTimers()

    eligibilityCalculator = EligibilityCalculator(eligibilityLayers)
    eligbility = eligibilityCalculator.determineEligibilityForPolygon(polygon)
    
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)

    logging.info(eligbility)
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    eligbilityRow = eligibilityCalculator.createOutputTableRow(polyId, [layer.upper() for layer in eligibilityLayers], eligbility)

    logging.info("Filter QEIA scores for polygon")
    
    (startWallTime, startProcessTime) = startTimers()
    filteredQeia = rawQeia.getFilteredMatrix(eligbility)
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)
    print(filteredQeia.createOutputTableRow())
    logging.info(f'Wall Time: {wallTime} milliseconds')
    logging.info(f'Process Time: {processTime} milliseconds')

    logging.info("Calculate action scores using priorities and filtered QEIA")
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMultiCriteriaDecisionAnalysisForParcel(weightedPriorityScores, filteredQeia)
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)
    print(mcda)
    print(mcda.transpose())
    logging.info(f'Wall Time: {wallTime} milliseconds')
    logging.info(f'Process Time: {processTime} milliseconds')

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
    parser.add_argument('-w', '--wkt', type=str, required=True, help="WKT file containing polygon geometry")
    parser.add_argument('-l', '--layer_config', type=str, required=False, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-q', '--qeia_matrix', type=str, required=False, help="Raw QEIA impact score matrix file")

    args = parser.parse_args()

    main(args.poly_id, args.wkt, args.layer_config, args.qeia_matrix)