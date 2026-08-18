import json
import argparse
import logging

from common.helpers import ConditionalFormatter, get_output_path, get_output_filename
from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from datetime import datetime
from priority_scores import extractPriorityScoresForInputPolygons, extractPercentagesForInputPolygons, calculatePriorityScoreWeighting, calculateActiveServices, calculateInitialPriorityScoreWeighting, groupColumnAggregation, mergeEligibilityOptions
from eligibility import calculateOptionEligibilityForInputPolygons
from mcda import calculateMCDAForPriorityScoresWithEligibility
from pathlib import Path
import pandas as pd
import numpy as np

loggingFormatStr = '%(levelname)s: %(asctime)s: %(message)s'
logging.basicConfig(
    level = logging.INFO, 
    format = loggingFormatStr
)

def main(polygonPath: str,
         polygonIdColumn: str,
         layerConfig: str,
         weightingsConfig: str,
         qeiaMatrix: str,
         usePrecalculatedPriorityScores: bool,
         calculatepercentages: bool,
         priorityScoreFilename: str,
         overwritePriorityScores: bool,
         overridePriorityScorePath: str,
         usePrecalculatedWeightedPriorityScores: bool,
         weightedPriorityScoreFilename: str,
         overwriteWeightedPriorityScores: bool,
         overrideWeightedPriorityScorePath: str,
         usePrecalcalculatedEligibilityOptions: bool,
         eligibilityOptionsFilename: str,
         overwriteEligibilityOptions: bool,
         precalculatedEligibilityIsArea: bool,
         overrideEligibilityOptionsPath: str,
         columnGroupConfigPath: str,
         activeServicesMatrixFilename: str,
         writeActiveServicesMatrix: bool,
         overrideActiveServicesMatrixPath: str,
         mcdaFilename: str,
         overwriteMcda: bool,
         overrideMcdaPath: str,
         outputPath: str,
         runName: str):
    '''Process a a set of input polygons through to MCDA, using weighted priority scores, eligible option layers and 
    an input QEIA matrix, function will output several intermediate CSV files during the process to help with rerunning
    the script with different options or pre-constructed inputs.

    Args:
        polygonPath (str): Path to vector input file containing the input polygons, should support most vector formats
        polygonIdColumn (str): The name of the ID column in the input vector file
        layerConfig (str): Path to a JSON file containing a configuration object for layers (priority and eligibility)
        weightingsConfig (str): Path to a JSON file containing a configuration object for priority weightings
        qeiaMatrix (str): Path to a JSON file containing a configuration object for a QEIA matrix to process against
        usePrecalculatedPriorityScores (bool): If true use the precalculated priority scores CSV file in the output path directory
        calculatepercentages (bool): If true, percentage coverage values will be extracted per class instead of maximum priority score touching parcel
        priorityScoreFilename (str): Filename for priority scores CSV file, this file will be written to / read from the output path directory
        overwritePriorityScores (bool): Overwrite priority scores file if it already exists
        overridePriorityScorePath (str): Override full path for priority scores file as CSV, None if not used
        usePrecalculatedWeightedPriorityScores (bool): If true use the precalculated weighted priority scores CSV file in the output path directory
        weightedPriorityScoreFilename (str): Filename for weighted priority scores CSV file, this file will be written to / read from the output path directory
        overwriteWeightedPriorityScores (bool): Overwrites weighted priority scores file if it already exists
        overrideWeightedPriorityScorePath (str): Override full path for weighted priority scores file as CSV, None if not used
        usePrecalcalculatedEligibilityOptions (bool): If true use the precalculated eligibility options CSV/Parquet file in the output path directory
        eligibilityOptionsFilename (str): Filename for eligibility options CSV file, this file will be written to / read from the output path directory
        eligibilityScoreOutputPath (str): Path to store intermediate eligibility options for the intput polygons
        overwriteEligibilityOptions (bool): Overwrites the eligibility options CSV file if it already exists
        precalculatedEligibilityIsArea (bool): If true the precalculated eligibility options file is expressed as area coverage rather than boolean
        overrideEligibilityOptionsPath (str): Override full path for eligibility options file as boolean table or area (CSV/Parquet), None if not used
        columnGroupConfigPath (str): Path to a JSON file containing a configuration object for column group aggregation
        activeServicesMatrixFilename (str): Filename for the active services matrix as a CSV
        writeActiveServicesMatrix (bool): Whether to write the active services matrix to a CSV file
        overrideActiveServicesMatrixPath (str): Override full path for active services matrix file as CSV, None if not used
        mcdaFilename (str): Filename for MCDA CSV file, this file will be written to the output path directory
        overwriteMcda (bool): Overwrite MCDA file output if it already exists
        overrideMcdaPath (str): Override full path for MCDA file as CSV, None if not used
        outputPath (str): Base output path to store results in
        runName (str): Optional run name to append to output file pre suffix and to create a subdirectory in the output path

    Raises:
        FileExistsError: Raised if a file exists and has not been set to be overwritten
        FileNotFoundError: Raised if an override file path has been set but the file does not exist
        ValueError: Raised if the input weightings config is not a superset of the intput priority layers
    '''
    finalOutputPath = get_output_path(outputPath if outputPath else '.', runName)

    # Create file handler for logging to output path directory and attach to root logger
    fileHandler = logging.FileHandler(finalOutputPath.joinpath(f'execution_{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'))
    fileHandler.formatter = ConditionalFormatter(loggingFormatStr)
    fileHandler.setLevel(logging.INFO)
    logging.getLogger().addHandler(fileHandler)
    
    logging.info(f'Using output path at {finalOutputPath}')

    if overridePriorityScorePath:
        finalPriorityScorePath = Path(overridePriorityScorePath)
        logging.info(f'Using override priority score path at {finalPriorityScorePath}')
    else:
        finalPriorityScorePath = finalOutputPath.joinpath(get_output_filename(priorityScoreFilename, runName))
        logging.info(f'Using priority score path at {finalPriorityScorePath}')

    if overrideWeightedPriorityScorePath:
        finalWeightedPriorityScorePath = Path(overrideWeightedPriorityScorePath)
        logging.info(f'Using override weighted priority score path at {finalWeightedPriorityScorePath}')
    else:
        finalWeightedPriorityScorePath = finalOutputPath.joinpath(get_output_filename(weightedPriorityScoreFilename, runName))
        logging.info(f'Using weighted priority score path at {finalWeightedPriorityScorePath}')

    if overrideActiveServicesMatrixPath:
        finalActiveServicesMatrixPath = Path(overrideActiveServicesMatrixPath)
        logging.info(f'Using override active services matrix path at {finalActiveServicesMatrixPath}')
    else:
        finalActiveServicesMatrixPath = finalOutputPath.joinpath(get_output_filename(activeServicesMatrixFilename, runName))
        logging.info(f'Using active services matrix path at {finalActiveServicesMatrixPath}')

    if overrideEligibilityOptionsPath:
        finalEligibilityOptionsPath = Path(overrideEligibilityOptionsPath)
        logging.info(f'Using override eligibility options path at {finalEligibilityOptionsPath}')
    else:
        finalEligibilityOptionsPath = finalOutputPath.joinpath(get_output_filename(eligibilityOptionsFilename, runName))
        logging.info(f'Using eligibility options path at {finalEligibilityOptionsPath}')
    
    if overrideMcdaPath:
        finalMcdaPath = Path(overrideMcdaPath)
        logging.info(f'Using override MCDA path at {finalMcdaPath}')
    else:
        finalMcdaPath = finalOutputPath.joinpath(get_output_filename(mcdaFilename, runName))
        logging.info(f'Using MCDA path at {finalMcdaPath}')
    
    (totalStartWallTime, totalStartProcessTime) = startTimers()
    
    with open(qeiaMatrix) as f:
        config = json.load(f)
        rawQeia = QEIAMatrix(config)

    logging.info(f'Imported Raw QEIA matrix')

    with open(layerConfig) as f:
        config = json.load(f)

    (procStartWallTime, procStartProcessTime) = startTimers()

    if usePrecalculatedWeightedPriorityScores and finalWeightedPriorityScorePath.exists():
        logging.info('Pre-calculated weighted priority scores found, skipping priority score calculation')
        logging.info('Reading pre-calculated weighted priority scores')
        weightedPriorityScores = pd.read_csv(finalWeightedPriorityScorePath)
        weightedPriorityScores.set_index(['id','option'], inplace=True)
    else:
        (startWallTime, startProcessTime) = startTimers()
        if usePrecalculatedPriorityScores and finalPriorityScorePath.exists():
            logging.info('Reading pre-calculated priority scores')
            priorityScores = pd.read_csv(finalPriorityScorePath)
            priorityScores.set_index('id', inplace=True)
        else:
            if finalPriorityScorePath.exists():
                if overwritePriorityScores:
                    logging.warning(f'Output path {finalPriorityScorePath} already exists, overwriting')
                else:
                    logging.warning(f'Output path {finalPriorityScorePath} already exists, exiting')
                    raise FileExistsError(f'Output path {finalPriorityScorePath} already exists')
            
            priorityLayers: dict[str, PriorityLayer] = {}
            priorityLayers = processPriorityLayers(config['priority_layers'])
            logging.info(f'Found {len(priorityLayers)} priority layers in the config file')
            
            logging.info('Calculate priority scores')
            if calculatepercentages:
                priorityPercentages = extractPercentagesForInputPolygons(Path(polygonPath), priorityLayers, polygonIdColumn)
                priorityPercentages.to_csv(finalPriorityScorePath, index=True, index_label='id')

            else:
                priorityScores = extractPriorityScoresForInputPolygons(Path(polygonPath), priorityLayers, polygonIdColumn)
                priorityScores.to_csv(finalPriorityScorePath, index=True, index_label='id')
        
        (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
        logging.info('---------------------------- Priority Score Extraction Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')
        logging.info(priorityScores, extra={'simple': True})

        (startWallTime, startProcessTime) = startTimers()
        logging.info('Calculating active services from priority scores')

        activeServicesMatrix = calculateActiveServices(priorityScores)
        
        if writeActiveServicesMatrix:
            activeServicesMatrix.to_csv(finalActiveServicesMatrixPath, index=True, index_label='id')
            
        activeServicesMatrix.drop(activeServicesMatrix.columns.difference(['id', 'totalServices']), axis=1, inplace=True)

        priorityScores = priorityScores.merge(activeServicesMatrix, on='id', how='left')
        logging.info('---------------------------- Active Serices Calculation Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

        if usePrecalcalculatedEligibilityOptions and finalEligibilityOptionsPath.exists():
            logging.info('Reading pre-calculated eligibility options')
            if Path(finalEligibilityOptionsPath).suffix == '.parquet':
                optionEligbility = pd.read_parquet(finalEligibilityOptionsPath)
                optionEligbility.set_index('id_parcel', inplace=True)
            else:
                optionEligbility = pd.read_csv(finalEligibilityOptionsPath)
                optionEligbility.set_index('id_parcel', inplace=True)
        elif precalculatedEligibilityIsArea and Path(finalEligibilityOptionsPath).exists():
            logging.info('Reading pre-calculated eligibility options as area')
            if Path(finalEligibilityOptionsPath).suffix == '.parquet':
                logging.info('Pre-calculated eligibility options as area is in parquet format, reading as such assuming RPA input')
                optionEligbilityAreas = pd.read_parquet(finalEligibilityOptionsPath)
                optionEligbilityAreas.set_index('id_parcel', inplace=True)
                # Convert to boolean options
                optionEligbility = optionEligbilityAreas.map(lambda x: not np.isnan(x))
                optionEligbility.index.names = ['id']
            else:
                optionEligbilityAreas = pd.read_csv(finalEligibilityOptionsPath)
                optionEligbilityAreas.set_index('id_parcel', inplace=True)
                optionEligbility = optionEligbilityAreas.map(lambda x: not np.isnan(x))
        else:
            if Path(finalEligibilityOptionsPath).exists():
                if overwriteEligibilityOptions:
                    logging.warning(f'Output path {finalEligibilityOptionsPath} already exists, overwriting')
                else:
                    logging.warning(f'Output path {finalEligibilityOptionsPath} already exists, exiting')
                    raise FileExistsError(f'Output path {finalEligibilityOptionsPath} already exists')

            logging.info('Determining polygon eligibility')

            eligibilityLayers: dict[str, EligibilityLayer] = {}
            eligibilityLayers = processEligibilityLayers(config['eligibility_layers'])
            
            (startWallTime, startProcessTime) = startTimers()

            optionEligbility = calculateOptionEligibilityForInputPolygons(Path(polygonPath), eligibilityLayers)
            optionEligbility.to_csv(finalEligibilityOptionsPath, index=True, index_label='id')
            
            (wallTime, processTime) = endTimers(startWallTime, startProcessTime, 1)
            
            logging.info('---------------------------- Eligibility Discovery Complete ---------------------------- ')
            logging.info(f'Wall Time: {wallTime} seconds')
            logging.info(f'Process Time: {processTime} seconds')
        logging.info(optionEligbility, extra={'simple': True})

        mergedPriorityScores = mergeEligibilityOptions(priorityScores, optionEligbility)

        (startWallTime, startProcessTime) = startTimers()
        logging.info('Aggregating group columns in priority scores')

        if columnGroupConfigPath:
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
        logging.info(mergedPriorityScores, extra={'simple': True})

        logging.info('---------------------------- Initial Priority Score Weighting Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

        logging.info('Calculating weighted priority scores')
        (startWallTime, startProcessTime) = startTimers()

        if (Path(finalWeightedPriorityScorePath).exists()):
            if overwriteWeightedPriorityScores:
                logging.warning(f'Output path {finalWeightedPriorityScorePath} already exists, overwriting')
            else:
                logging.warning(f'Output path {finalWeightedPriorityScorePath} already exists, exiting')
                raise FileExistsError(f'Output path {finalWeightedPriorityScorePath} already exists')

        with open(weightingsConfig) as f:
            weightings = json.load(f)
            if not set(weightings.keys()).issuperset(mergedPriorityScores.keys().to_list()):
                raise ValueError('Mismatch between priority layers and weightings')

        weightedPriorityScores = calculatePriorityScoreWeighting(mergedPriorityScores, weightings)
        weightedPriorityScores.to_csv(finalWeightedPriorityScorePath)
        logging.info(weightedPriorityScores, extra={'simple': True})
        
        logging.info('---------------------------- Priority Score Weighting Complete ---------------------------- ')
        logging.info(f'Wall Time: {wallTime} seconds')
        logging.info(f'Process Time: {processTime} seconds')

    logging.info('Calculate action scores using priorities and QEIA')
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia)

    if Path(finalMcdaPath).exists() and not overwriteMcda:
        logging.warning(f'Output path {finalMcdaPath} already exists, exiting')
        raise FileExistsError(f'Output path {finalMcdaPath} already exists')
    
    mcda.to_csv(finalMcdaPath)

    (wallTime, processTime) = endTimers(startWallTime, startProcessTime)
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
    parser = argparse.ArgumentParser(description='Generate action scores for a set of input polygons using priority scores, eligibility options and a QEIA matrix')
    parser.add_argument('-i', '--polygon-source', type=str, required=True, help='Unique ID for the polygon')
    parser.add_argument('-c', '--polygon-id-column', type=str, required=False, default='NGC', help='Column name for the polygon ID')
    parser.add_argument('-l', '--layer-config', type=str, required=False, default='layers.json', help='JSON file containing priority and eligibility layers')
    parser.add_argument('-w', '--weightings-config', type=str, required=False, default='weightings.json', help='JSON file containing priority weightings')
    parser.add_argument('-q', '--qeia-matrix', type=str, required=False, help='Raw QEIA impact score matrix file')
    parser.add_argument('--use-precalculated-priority-scores', required=False, help='Use precalculated priority scores table as a CSV', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--priority-score-filename', type=str, required=False, help='Filename for priority scores table as CSV for this run', default='priority_scores.csv')
    parser.add_argument('--overwrite-priority-scores', required=False, help='Overwrite existing prioirity scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-priority-score-path', type=str, required=False, help='Full path to an optional file for priority scores as CSV', default=None)
    parser.add_argument('--use-precalculated-weighted-priority-scores', required=False, help='Use precalculated weighted priority scores table as a CSV', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--weighted-priority-score-filename', type=str, required=False, help='Filename for weighted prioirity scores table as CSV for this run', default='weighted_priority_scores.csv')
    parser.add_argument('--overwrite-weighted-priority-scores', required=False, help='Overwrite existing weigthed prioirity scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-weighted-priority-score-path', type=str, required=False, help='Full path to an optional file for weighted priority scores as CSV', default=None)
    parser.add_argument('--active-services-matrix-filename', type=str, required=False, help='Filename for active services matrix as CSV for this run, if blank dont write', default='active_services.csv')
    parser.add_argument('--write-active-services-matrix', required=False, help='Whether to write the active services matrix to a CSV file', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-active-services-matrix-path', type=str, required=False, help='Full path to an optional file for active services matrix as CSV', default=None)
    parser.add_argument('--use-precalculated-eligibility-options', required=False, help='Use precalculated eligiblity options table as a CSV/Parquet', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--eligibility-options-filename', type=str, required=False, help='Filename for eligibility options table as CSV for this run', default='eligibility.csv')
    parser.add_argument('--overwrite-eligiblity-options', required=False, help='Overwrite existing option eligiblity table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--precalculated-eligibility-is-area', required=False, help='Optional path precalculated option eligiblity table is expresssed as a coverage area', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-eligibility-options-path', type=str, required=False, help='Full path to an optional file for eligibility options as CSV/Parquet', default=None)
    parser.add_argument('--column-group-config-path', type=str, required=False, help='Path to a JSON file containing a configuration object for column group aggregation', default=None)
    parser.add_argument('--mcda-filename', type=str, required=False, help='Filename for MCDA table as CSV for this run', default='mcda.csv')
    parser.add_argument('--overwrite-mcda', required=False, help='Overwrite existing MCDA table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-mcda-path', type=str, required=False, help='Full path to an optional file for MCDA table as CSV', default=None)
    parser.add_argument('--output-path', type=str, required=True, help='Base output path to store results in')
    parser.add_argument('--run-name', type=str, required=False, help='Optional run name to append to output file pre suffix', default=None)

    args = parser.parse_args()

    main(
        args.polygon_source, 
        args.polygon_id_column, 
        args.layer_config, 
        args.weightings_config,
        args.qeia_matrix, 
        args.use_precalculated_priority_scores, 
        args.priority_score_filename, 
        args.overwrite_priority_scores, 
        args.override_priority_score_path,
        args.use_precalculated_weighted_priority_scores, 
        args.weighted_priority_score_filename, 
        args.overwrite_weighted_priority_scores, 
        args.override_weighted_priority_score_path,
        args.use_precalculated_eligibility_options, 
        args.eligibility_options_filename,
        args.overwrite_eligiblity_options, 
        args.precalculated_eligibility_is_area,
        args.override_eligibility_options_path,
        args.column_group_config_path,
        args.active_services_matrix_filename,
        args.write_active_services_matrix,
        args.override_active_services_matrix_path,
        args.mcda_filename,
        args.overwrite_mcda,
        args.override_mcda_path,
        args.output_path,
        args.run_name
    )
