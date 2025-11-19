import json
import argparse
import logging
import shapely

from common.helpers import ConditionalFormatter, get_output_path, get_output_filename
from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from datetime import datetime
from priority_scores import extractPriorityScoresForInputPolygon, calculateActiveServices, calculateInitialPriorityScoreWeighting, calculatePriorityScoreWeighting, groupColumnAggregation, mergeEligibilityOptions
from eligibility import calculateOptionEligibilityForInputPolygon
from mcda import calculateMCDAForPriorityScoresWithEligibility
from pathlib import Path

loggingFormatStr = '%(levelname)s: %(asctime)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=loggingFormatStr)

def main(polyId: str, wkt: str, layerConfig: str, weightingsConfig: str, columnGroupConfigPath: str, qeiaMatrix: str, outputPath: str, runName: str):
    """Process a single polygon through to MCDA, using weighted priority scores,
    eligible option layers and an input QEIA matrix

    Args:
        polyId (str): An ID for this polygon
        wkt (str): A path to a WKT file describing the input polygon as WKT (in the same projection as the eligibility and priority layers)
        layerConfig (str): Path to a JSON file containing a configuration object for layers (priority and eligibility)
        columnGroupConfigPath (str): Path to a JSON file containing a configuration object for column group aggregation
        qeiaMatrix (str): Path to a JSON file containing a configuration object for a QEIA matrix to process against
        output (str): Optional path to store MCDA output to as a .csv file
    """
    outputPath = get_output_path(outputPath, runName)

    # Create file handler for logging to output path directory and attach to root logger
    fileHandler = logging.FileHandler(outputPath.joinpath(f'single_polygon_execution_{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'))
    fileHandler.formatter = ConditionalFormatter(loggingFormatStr)
    fileHandler.setLevel(logging.INFO)
    logging.getLogger().addHandler(fileHandler)

    finalActiveServicesPath = outputPath.joinpath(get_output_filename('active_services.csv', runName))
    finalPriorityScoresPath = outputPath.joinpath(get_output_filename('priority_scores.csv', runName))
    finalWeightedPriorityScoresPath = outputPath.joinpath(get_output_filename('weighted_priority_scores.csv', runName))
    finalEligibilityPath = outputPath.joinpath(get_output_filename('eligibility_options.csv', runName))
    finalMCDAPath = outputPath.joinpath(get_output_filename('mcda.csv', runName))

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
    priorityScores.to_csv(finalPriorityScoresPath, index=True, index_label='id')
    
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
    logging.info('---------------------------- Priority Scores Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')
    logging.info(priorityScores, extra={'simple': True})
    
    (startWallTime, startProcessTime) = startTimers()
    logging.info('Calculating active services from priority scores')

    activeServicesMatrix = calculateActiveServices(priorityScores, "", False)
    activeServicesMatrix.to_csv(finalActiveServicesPath, index=True, index_label='id')
    activeServicesMatrix.drop(activeServicesMatrix.columns.difference(['id', 'totalServices']), axis=1, inplace=True)
    logging.info(activeServicesMatrix, extra={'simple': True})

    priorityScores = priorityScores.merge(activeServicesMatrix, on='id', how='left')
    logging.info('---------------------------- Active Serices Calculation Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    logging.info('Determining polygon eligibility')

    eligibilityLayers: dict[str, EligibilityLayer] = {}
    eligibilityLayers = processEligibilityLayers(config['eligibility_layers'])
        
    (startWallTime, startProcessTime) = startTimers()

    optionEligbility = calculateOptionEligibilityForInputPolygon(polyId, polygon, eligibilityLayers)
    optionEligbility.to_csv(finalEligibilityPath, index=True, index_label='id')
        
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
    logging.info('---------------------------- Eligibility Discovery Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')
    logging.info(optionEligbility, extra={'simple': True})

    mergedPriorityScores = mergeEligibilityOptions(priorityScores, optionEligbility)

    (startWallTime, startProcessTime) = startTimers()
    logging.info('Aggregating group columns in priority scores')

    if columnGroupConfigPath.strip():
        if not Path(columnGroupConfigPath).exists():
            raise FileNotFoundError(f'Column group config file {columnGroupConfigPath} does not exist')
        
        logging.info(f'Using column group config file {columnGroupConfigPath}')
        with open(columnGroupConfigPath) as config:
            columnGroupConfig = json.load(config)
        
        for columnGroup in columnGroupConfig.keys():
            logging.info(f'Aggregating column group {columnGroup}')

            mergedPriorityScores = groupColumnAggregation(mergedPriorityScores, columnGroup, columnGroupConfig[columnGroup]['options'], columnGroupConfig[columnGroup]['operation'])
    
    logging.info(mergedPriorityScores, extra={'simple': True})

    logging.info('---------------------------- Column Group Aggregation Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    (startWallTime, startProcessTime) = startTimers()
    logging.info('Initial Priority Score Weighting')

    mergedPriorityScores = calculateInitialPriorityScoreWeighting(mergedPriorityScores)
    logging.info(mergedPriorityScores)

    logging.info('---------------------------- Initial Priority Score Weighting Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    logging.info('Calculating weighted priority scores')
    (startWallTime, startProcessTime) = startTimers()

    with open(weightingsConfig) as f:
        weightings = json.load(f)
        if not set(weightings.keys()).issuperset(mergedPriorityScores.keys().to_list()):
            raise ValueError('Mismatch between priority layers and weightings')

    weightedPriorityScores = calculatePriorityScoreWeighting(mergedPriorityScores, weightings)
    weightedPriorityScores.to_csv(finalWeightedPriorityScoresPath, index=True)
    logging.info(weightedPriorityScores)
    
    logging.info('---------------------------- Priority Score Weighting Complete ---------------------------- ')
    logging.info(f'Wall Time: {wallTime} seconds')
    logging.info(f'Process Time: {processTime} seconds')

    logging.info("Calculate action scores using priorities and QEIA")
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia)
    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)
    mcda.to_csv(finalMCDAPath, index=True)
    logging.info(mcda, extra={'simple': True})
    
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate action scores for a given polygon land parcel")
    parser.add_argument('-i', '--polygon-id', type=str, required=True, help="Unique ID for the polygon")
    parser.add_argument('-p', '--polygon-wkt', type=str, required=True, help="WKT file containing polygon geometry")
    parser.add_argument('-l', '--layer-config', type=str, required=True, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-c', '--column-group-config-path', type=str, required=False, default="", help="JSON file containing column group aggregation configuration")
    parser.add_argument('-w', '--weightings-config', type=str, required=True, default="weightings.json", help="JSON file containing priority weightings")
    parser.add_argument('-q', '--qeia-matrix', type=str, required=True, help="Raw QEIA impact score matrix file")
    parser.add_argument('--output-path', type=str, required=True, help='Base output path to store results in')
    parser.add_argument('--run-name', type=str, required=False, help='Optional run name to append to output file pre suffix', default=None)

    args = parser.parse_args()

    main(args.poly_id, args.polygon_wkt, args.layer_config, args.weightings_config, args.qeia_matrix, args.output)