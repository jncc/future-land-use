import json
import argparse
import logging

from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from priority_scores import extractPriorityScoresForInputPolygons, calculatePriorityScoreWeighting, calculateActiveServices, calculateInitialPriorityScoreWeighting, groupColumnAggregation, mergeEligibilityOptions
from eligibility import calculateOptionEligibilityForInputPolygons
from mcda import calculateMCDAForPriorityScoresWithEligibility
from pathlib import Path
import pandas as pd
import numpy as np

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
         precalculatedEligibilityAsArea: str,
         eligibilityScoreOutputPath: str, 
         overwriteEligibilityScores: bool,
         columnGroupConfigPath: str,
         activeServicesMatrixPath: str,
         mcda_output_path: str,
         overwrite_mcda_output: bool):
    '''Process a a set of input polygons through to MCDA, using weighted priority scores, eligible option layers and 
    an input QEIA matrix, function will output several intermediate CSV files during the process to help with rerunning
    the script with different options or pre-constructed inputs.

    Args:
        polygonPath (str): Path to vector input file containing the input polygons, should support most vector formats
        polygonIdColumn (str): The name of the ID column in the input vector file
        layerConfig (str): Path to a JSON file containing a configuration object for layers (priority and eligibility)
        weightingsConfig (str): Path to a JSON file containing a configuration object for priority weightings
        qeiaMatrix (str): Path to a JSON file containing a configuration object for a QEIA matrix to process against
        precalculatedPriorityScores (str): Optional, if not None use this path to load an existing CSV file output of the priority scores
        priorityScoreOutputPath (str): Path to store intermediate priority scores to as a CSV
        overwritePriorityScores (bool): Overwrite priority scores file if it already exists
        precalculatedWeightedPrioirityScores (str): Optional, if not None use this path to load an existing CSV output of weighted priority scores
        weightedPriorityScoreOutputPath (str): Path to store intermediate weighted priority scores to as a CSV
        overwriteWeightedPriorityScores (bool): Overwrites weighted priority scores file if it already exists
        precalculatedEligibility (str): Optional, if not none use this path to load an existing output of eligibilty options per polygon (CSV/Parquet)
        precalculated_eligibility_as_area (str): Optional, if not none use this path to load an existing output of eligibilty options as area per polygon (CSV/Parquet)
        eligibilityScoreOutputPath (str): Path to store intermediate eligibility options for the intput polygons
        overwriteEligibilityScores (bool): Overwrites the eligibility options CSV file if it already exists
        columnGroupConfigPath (str): Path to a JSON file containing a configuration object for column group aggregation
        activeServicesMatrixPath (str): Path to store the active services matrix as a CSV, if blank dont write
        mcda_output_path (str): Path to write final MCDA output file to
        overwrite_mcda_output (bool): Overwrite MCDA file output if it already exists

    Raises:
        FileExistsError: Raised if a file exists and has not been set to be overwritten
        ValueError: Raised if the input weightings config is not a superset of the intput priority layers
    '''
    (totalStartWallTime, totalStartProcessTime) = startTimers()
    
    with open(qeiaMatrix) as f:
        config = json.load(f)
        rawQeia = QEIAMatrix(config)

    logging.info(f'Imported Raw QEIA matrix')

    with open(layerConfig) as f:
        config = json.load(f)

    (procStartWallTime, procStartProcessTime) = startTimers()

    if precalculatedWeightedPrioirityScores and Path(precalculatedWeightedPrioirityScores).exists():
        logging.info('Pre-calculated weighted priority scores found, skipping priority score calculation')
        logging.info('Reading pre-calculated weighted priority scores')
        weightedPriorityScores = pd.read_csv(precalculatedWeightedPrioirityScores)
        weightedPriorityScores.set_index(['id','option'], inplace=True)
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
            
            priorityLayers: dict[str, PriorityLayer] = {}
            priorityLayers = processPriorityLayers(config['priority_layers'])
            logging.info(f'Found {len(priorityLayers)} priority layers in the config file')
            
            logging.info('Calculate priority scores')
            priorityScores = extractPriorityScoresForInputPolygons(Path(polygonPath), priorityLayers, polygonIdColumn)
            priorityScores.to_csv(priorityScoreOutputPath, index=True, index_label='id')
        
        (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
        logging.info('---------------------------- Priority Score Extraction Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')
        print(priorityScores)

        (startWallTime, startProcessTime) = startTimers()
        logging.info('Calculating active services from priority scores')

        activeServicesMatrix = calculateActiveServices(priorityScores, activeServicesMatrixPath, activeServicesMatrixPath.strip() != '')
        activeServicesMatrix.drop(activeServicesMatrix.columns.difference(['id', 'totalServices']), axis=1, inplace=True)

        priorityScores = priorityScores.merge(activeServicesMatrix, on='id', how='left')
        logging.info('---------------------------- Active Serices Calculation Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

        if precalculatedEligibility and Path(precalculatedEligibility).exists():
            logging.info('Reading pre-calculated eligibility options')
            if Path(precalculatedEligibility).suffix == '.parquet':
                optionEligbility = pd.read_parquet(precalculatedEligibility)
                optionEligbility.set_index('id', inplace=True)
            else:
                optionEligbility = pd.read_csv(precalculatedEligibility)
                optionEligbility.set_index('id', inplace=True)
        elif precalculatedEligibilityAsArea and Path(precalculatedEligibilityAsArea).exists():
            logging.info('Reading pre-calculated eligibility options as area')
            if Path(precalculatedEligibilityAsArea).suffix == '.parquet':
                logging.info('Pre-calculated eligibility options as area is in parquet format, reading as such assuming RPA input')
                optionEligbilityAreas = pd.read_parquet(precalculatedEligibilityAsArea)
                optionEligbilityAreas.set_index('id_parcel', inplace=True)
                # Convert to boolean options
                optionEligbility = optionEligbilityAreas.map(lambda x: not np.isnan(x))
                optionEligbility.index.names = ['id']
            else:
                optionEligbilityAreas = pd.read_csv(precalculatedEligibilityAsArea)
                optionEligbilityAreas.set_index('id_parcel', inplace=True)
                optionEligbility = optionEligbilityAreas.map(lambda x: not np.isnan(x))
        else:
            if Path(eligibilityScoreOutputPath).exists():
                if overwriteEligibilityScores:
                    logging.warning(f'Output path {eligibilityScoreOutputPath} already exists, overwriting')
                else:
                    logging.warning(f'Output path {eligibilityScoreOutputPath} already exists, exiting')
                    raise FileExistsError(f'Output path {eligibilityScoreOutputPath} already exists')

            logging.info('Determining polygon eligibility')

            eligibilityLayers: dict[str, EligibilityLayer] = {}
            eligibilityLayers = processEligibilityLayers(config['eligibility_layers'])
            
            (startWallTime, startProcessTime) = startTimers()

            optionEligbility = calculateOptionEligibilityForInputPolygons(Path(polygonPath), eligibilityLayers)
            optionEligbility.to_csv(eligibilityScoreOutputPath, index=True, index_label='id')
            
            (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
            
            logging.info('---------------------------- Eligibility Discovery Complete ---------------------------- ')
            logging.info(f'Wall Time: {wallTime} seconds')
            logging.info(f'Process Time: {processTime} seconds')
        print(optionEligbility)

        mergedPriorityScores = mergeEligibilityOptions(priorityScores, optionEligbility)

        (startWallTime, startProcessTime) = startTimers()
        logging.info('Aggregating group columns in priority scores')

        if columnGroupConfigPath.strip():
            with open(columnGroupConfigPath) as config:
                columnGroupConfig = json.load(config)
            
            for columnGroup in columnGroupConfig.keys():
                logging.info(f'Aggregating column group {columnGroup}')

                mergedPriorityScores = groupColumnAggregation(mergedPriorityScores, columnGroup, columnGroupConfig[columnGroup]['options'], columnGroupConfig[columnGroup]['operation'])
        
        print(mergedPriorityScores)

        logging.info('---------------------------- Column Group Aggregation Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

        (startWallTime, startProcessTime) = startTimers()
        logging.info('Initial Priority Score Weighting')

        mergedPriorityScores = calculateInitialPriorityScoreWeighting(mergedPriorityScores)
        print(mergedPriorityScores)

        logging.info('---------------------------- Initial Priority Score Weighting Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

        logging.info('Calculating weighted priority scores')
        (startWallTime, startProcessTime) = startTimers()

        if (Path(weightedPriorityScoreOutputPath).exists()):
            if overwriteWeightedPriorityScores:
                logging.warning(f'Output path {weightedPriorityScoreOutputPath} already exists, overwriting')
            else:
                logging.warning(f'Output path {weightedPriorityScoreOutputPath} already exists, exiting')
                raise FileExistsError(f'Output path {weightedPriorityScoreOutputPath} already exists')

        with open(weightingsConfig) as f:
            weightings = json.load(f)
            if not set(weightings.keys()).issuperset(mergedPriorityScores.keys().to_list()):
                raise ValueError('Mismatch between priority layers and weightings')

        weightedPriorityScores = calculatePriorityScoreWeighting(mergedPriorityScores, weightings)
        weightedPriorityScores.to_csv(weightedPriorityScoreOutputPath)
        print(weightedPriorityScores)
        
        logging.info('---------------------------- Priority Score Weighting Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

    logging.info('Calculate action scores using priorities and QEIA')
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia)

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
    parser = argparse.ArgumentParser(description='Generate action scores for a given polygon land parcel')
    parser.add_argument('-i', '--poly_source', type=str, required=True, help='Unique ID for the polygon')
    parser.add_argument('-c', '--polygon_id_column', type=str, required=False, default='NGC', help='Column name for the polygon ID')
    parser.add_argument('-l', '--layer_config', type=str, required=False, default='layers.json', help='JSON file containing priority and eligibility layers')
    parser.add_argument('-w', '--weightings_config', type=str, required=False, default='weightings.json', help='JSON file containing priority weightings')
    parser.add_argument('-q', '--qeia_matrix', type=str, required=False, help='Raw QEIA impact score matrix file')
    parser.add_argument('--precalculated_priority_scores', type=str, required=False, help='Optional path precalculated priority scores table as a CSV', default=None)
    parser.add_argument('--priority_score_output_path', type=str, required=False, help='Path to output prioirity scores table as CSV for this run', default='priority_scores.csv')
    parser.add_argument('--overwrite_priority_score_output', type=bool, required=False, help='Overwrite existing prioirity scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--precalculated_weighted_priority_scores', type=str, required=False, help='Optional path precalculated weighted priority scores table as a CSV', default=None)
    parser.add_argument('--weighted_priority_score_output_path', type=str, required=False, help='Path to output prioirity scores table as CSV for this run', default='weighted_priority_scores.csv')
    parser.add_argument('--overwrite_weighted_priority_score_output', type=bool, required=False, help='Overwrite existing weigthed prioirity scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--precalculated_eligibility', type=str, required=False, help='Optional path precalculated option eligiblity table expressed as boolean options (CSV/Parquet)', default=None)
    parser.add_argument('--precalculated_eligibility_as_area', type=str, required=False, help='Optional path precalculated option eligiblity table expresssed as a coverage area (CSV/Parquet)', default=None)
    parser.add_argument('--eligibility_options_id_column', type=str, required=False, help='Name of the ID column in the eligibility dataset', default='id_parcel')
    parser.add_argument('--eligibility_options_output_path', type=str, required=False, help='Path to output eligibility options table as CSV for this run', default='eligibility.csv')
    parser.add_argument('--column_group_config_path', type=str, required=False, help='Path to a JSON file containing a configuration object for column group aggregation', default='')
    parser.add_argument('--active_services_matrix_path', type=str, required=False, help='Path to output active services matrix as CSV for this run, if blank dont write', default='')
    parser.add_argument('--overwrite_eligiblity_output', type=bool, required=False, help='Overwrite existing option eligiblity table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--mcda_output_path', type=str, required=False, help='Path to output MCDA table as CSV for this run', default='mcda.csv')
    parser.add_argument('--overwrite_mcda_output', type=bool, required=False, help='Overwrite existing MCDA table if it exists', default=False, action=argparse.BooleanOptionalAction)

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
        args.precalculated_eligibility_as_area,
        args.eligibility_options_output_path, 
        args.overwrite_eligiblity_output,
        args.column_group_config_path,
        args.active_services_matrix_path,
        args.mcda_output_path,
        args.overwrite_mcda_output
    )
