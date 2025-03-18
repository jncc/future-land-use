import json
import argparse
import logging
import shapely

from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from priority_scores import calculatePriorityScoresForInputPolygons, calculateWeightedPriorityScores
from eligibility import calculateOptionEligibilityForInputPolygons
from mcda import calculateMCDAForPriorityScoresWithEligibility
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')
    
def main(polygonPath: str,
         polygonIdColumn: str,
         layerConfig: str,
         weightingsConfig: str,
         qeiaMatrix: str,
         precalculatedPriorityScores: str,
         priorityScoreOutputPath: str,
         overwritePriorityScores: bool,
         precalculatedWeightedPrioirityScores: str,
         weightedPriorityScoreOutputPath: str,
         overwriteWeightedPriorityScores: bool,
         precalculatedEligibility: str, 
         eligibilityScoreOutputPath: str, 
         overwriteEligibilityScores: bool,
         mcda_output_path: str,
         overwrite_mcda_output: bool):
    """Process a single polygon through to MCDA, using weighted priority scores,
    eligible option layers and an input QEIA matrix

    Args:
        polyId (str): An ID for this polygon
        wkt (str): A path to a WKT file describing the input polygon as WKT (in the same projection as the eligibility and priority layers)
        layerConfig (str): Path to a JSON file containing a configuration object for layers (priority and eligibility)
        qeiaMatrix (str): Path to a JSON file containing a configuration object for a QEIA matrix to process against
    """
    (totalStartWallTime, totalStartProcessTime) = startTimers()

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
    (procStartWallTime, procStartProcessTime) = startTimers()

    if precalculatedWeightedPrioirityScores and Path(precalculatedWeightedPrioirityScores).exists():
        logging.info('Pre-calculated weighted priority scores found, skipping priority score calculation')
        logging.info('Reading pre-calculated weighted priority scores')
        weightedPriorityScores = pd.read_csv(precalculatedWeightedPrioirityScores)
        weightedPriorityScores.set_index('id', inplace=True)
    else:
        (startWallTime, startProcessTime) = startTimers()
        if precalculatedPriorityScores and Path(precalculatedPriorityScores).exists():
            logging.info('Reading pre-calculated priority scores')
            priorityScores = pd.read_csv(precalculatedPriorityScores)
            priorityScores.set_index('id', inplace=True)
        else:
            if (Path(priorityScoreOutputPath).exists()):
                if overwritePriorityScores:
                    logging.warning(f'Output path {priorityScoreOutputPath} already exists, overwriting')
                else:
                    logging.warning(f'Output path {priorityScoreOutputPath} already exists, exiting')
                    raise FileExistsError(f'Output path {priorityScoreOutputPath} already exists')
            
            logging.info('Calculate priority scores')
            priorityScores = calculatePriorityScoresForInputPolygons(Path(polygonPath), priorityLayers, polygonIdColumn)
            priorityScores.to_csv(priorityScoreOutputPath, index=True, index_label='id')
        
        (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
        logging.info('---------------------------- Priority Scores Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')
        print(priorityScores)

        logging.info('Calculating weighted priority scores')
        (startWallTime, startProcessTime) = startTimers()

        if (Path(weightedPriorityScoreOutputPath).exists()):
            if overwriteWeightedPriorityScores:
                logging.warning(f'Output path {priorityScoreOutputPath} already exists, overwriting')
            else:
                logging.warning(f'Output path {priorityScoreOutputPath} already exists, exiting')
                raise FileExistsError(f'Output path {priorityScoreOutputPath} already exists')
            
        weightedPriorityScores = calculateWeightedPriorityScores(priorityScores, weightings)
        weightedPriorityScores.to_csv(weightedPriorityScoreOutputPath, index=True, index_label='id')
    
        (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

        logging.info('---------------------------- Weighted Priority Scores Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} milliseconds')
        logging.info(f'Process Time: {processTime} milliseconds')
        print(weightedPriorityScores)

    if precalculatedEligibility and Path(precalculatedEligibility).exists():
        logging.info('Reading pre-calculated eligibility options')
        optionEligbility = pd.read_csv(precalculatedEligibility)
        optionEligbility.set_index('id', inplace=True)
    else:
        if Path(eligibilityScoreOutputPath).exists():
            if overwriteEligibilityScores:
                logging.warning(f'Output path {eligibilityScoreOutputPath} already exists, overwriting')
            else:
                logging.warning(f'Output path {eligibilityScoreOutputPath} already exists, exiting')
                raise FileExistsError(f'Output path {eligibilityScoreOutputPath} already exists')

        logging.info('Determining polygon eligibility')
        (startWallTime, startProcessTime) = startTimers()

        optionEligbility = calculateOptionEligibilityForInputPolygons(Path(polygonPath), eligibilityLayers)
        optionEligbility.to_csv(eligibilityScoreOutputPath, index=True, index_label='id')
        
        (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
        
        logging.info('---------------------------- Eligibility Discovery Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')
    print(optionEligbility)

    logging.info("Calculate action scores using priorities and QEIA")
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia, optionEligbility)

    if Path(mcda_output_path).exists() and not overwrite_mcda_output:
        logging.warning(f'Output path {mcda_output_path} already exists, exiting')
        raise FileExistsError(f'Output path {mcda_output_path} already exists')
    
    mcda.to_csv(mcda_output_path)

    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)
    print(mcda)
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
    parser.add_argument('-i', '--poly_source', type=str, required=True, help="Unique ID for the polygon")
    parser.add_argument('-c', '--polygon_id_column', type=str, required=False, default="NGC", help="Column name for the polygon ID")
    parser.add_argument('-l', '--layer_config', type=str, required=False, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-w', '--weightings_config', type=str, required=False, default="weightings.json", help="JSON file containing priority weightings")
    parser.add_argument('-q', '--qeia_matrix', type=str, required=False, help="Raw QEIA impact score matrix file")
    parser.add_argument('--precalculated_priority_scores', type=str, required=False, help="Optional path precalculated priority scores table as a CSV", default=None)
    parser.add_argument('--priority_score_output_path', type=str, required=False, help="Path to output prioirity scores table as CSV for this run", default="priority_scores.csv")
    parser.add_argument('--overwrite_priority_score_output', type=bool, required=False, help="Overwrite existing prioirity scores table if it exists", default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--precalculated_weighted_priority_scores', type=str, required=False, help="Optional path precalculated weighted priority scores table as a CSV", default=None)
    parser.add_argument('--weighted_priority_score_output_path', type=str, required=False, help="Path to output prioirity scores table as CSV for this run", default="weighted_priority_scores.csv")
    parser.add_argument('--overwrite_weighted_priority_score_output', type=bool, required=False, help="Overwrite existing weigthed prioirity scores table if it exists", default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--precalculated_eligibility', type=str, required=False, help="Optional path precalculated option eligiblity table as a CSV", default=None)
    parser.add_argument('--eligibility_options_output_path', type=str, required=False, help="Path to output eligibility options table as CSV for this run", default="eligibility.csv")
    parser.add_argument('--overwrite_eligiblity_output', type=bool, required=False, help="Overwrite existing option eligiblity table if it exists", default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--mcda_output_path', type=str, required=False, help="Path to output MCDA table as CSV for this run", default="mcda.csv")
    parser.add_argument('--overwrite_mcda_output', type=bool, required=False, help="Overwrite existing MCDA table if it exists", default=False, action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    main(
        args.poly_source, 
        args.polygon_id_column, 
        args.layer_config, 
        args.weightings_config,
        args.qeia_matrix, 
        args.precalculated_priority_scores, 
        args.priority_score_output_path, 
        args.overwrite_priority_score_output, 
        args.precalculated_weighted_priority_scores, 
        args.weighted_priority_score_output_path, 
        args.overwrite_weighted_priority_score_output, 
        args.precalculated_eligibility, 
        args.eligibility_options_output_path, 
        args.overwrite_eligiblity_output,
        args.mcda_output_path,
        args.overwrite_mcda_output
    )