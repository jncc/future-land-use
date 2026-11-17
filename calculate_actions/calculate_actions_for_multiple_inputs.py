import json
import argparse
import logging

from common.helpers import ConditionalFormatter, get_output_path, get_output_filename
from common.layers import PriorityLayer, processPriorityLayers
from common.qeia import QEIAMatrix
from datetime import datetime
from priority_scores import extractPriorityScoresForInputPolygons, calculatePriorityScoreWeighting, calculateActiveServices, calculateInitialPriorityScoreWeighting, groupColumnAggregation, mergeEligibilityOptions
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
         priorityScoreFilename: str,
         overwritePriorityScores: bool,
         overridePriorityScorePath: str,
         usePrecalculatedWeightedPriorityScores: bool,
         weightedPriorityScoreFilename: str,
         overwriteWeightedPriorityScores: bool,
         overrideWeightedPriorityScorePath: str,
         eligibilityOptionsPath: str,
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
        priorityScoreFilename (str): Filename for priority scores CSV file, this file will be written to / read from the output path directory
        overwritePriorityScores (bool): Overwrite priority scores file if it already exists
        overridePriorityScorePath (str): Override full path for priority scores file as CSV, None if not used
        usePrecalculatedWeightedPriorityScores (bool): If true use the precalculated weighted priority scores CSV file in the output path directory
        weightedPriorityScoreFilename (str): Filename for weighted priority scores CSV file, this file will be written to / read from the output path directory
        overwriteWeightedPriorityScores (bool): Overwrites weighted priority scores file if it already exists
        overrideWeightedPriorityScorePath (str): Override full path for weighted priority scores file as CSV, None if not used
        eligibilityOptionsPath (str): Path to a CSV/Parquet file containing eligibility options for the input polygons
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

    if overrideMcdaPath:
        finalMcdaPath = Path(overrideMcdaPath)
        logging.info(f'Using override MCDA path at {finalMcdaPath}')
    else:
        finalMcdaPath = finalOutputPath.joinpath(get_output_filename(mcdaFilename, runName))
        logging.info(f'Using MCDA path at {finalMcdaPath}')
    
    with open(qeiaMatrix) as f:
        config = json.load(f)
        rawQeia = QEIAMatrix(config)
    logging.info(f'Imported Raw QEIA matrix')

    with open(layerConfig) as f:
        config = json.load(f)

    if usePrecalculatedWeightedPriorityScores and finalWeightedPriorityScorePath.exists():
        logging.info('Pre-calculated weighted priority scores found, skipping priority score calculation')
        logging.info('Reading pre-calculated weighted priority scores')
        weightedPriorityScores = pd.read_csv(finalWeightedPriorityScorePath)
        weightedPriorityScores.set_index(['id','option'], inplace=True)
    else:
        if usePrecalculatedPriorityScores and finalPriorityScorePath.exists():
            logging.info('Reading pre-calculated priority scores')
            priorityScores = pd.read_csv(finalPriorityScorePath)
            priorityScores.set_index('id', inplace=True)
        else:
            if finalPriorityScorePath.exists():
                if overwritePriorityScores:
                    logging.warning(f'Output path {finalPriorityScorePath} already exists, overwriting')
                else:
                    raise FileExistsError(f'Output path {finalPriorityScorePath} already exists, use --overwrite-priority-scores to overwrite')
            
            priorityLayers: dict[str, PriorityLayer] = {}
            priorityLayers = processPriorityLayers(config['priority_layers'])
            logging.info(f'Found {len(priorityLayers)} priority layers in the config file')
            
            logging.info('Calculate priority scores')
            priorityScores = extractPriorityScoresForInputPolygons(Path(polygonPath), priorityLayers, polygonIdColumn)
            priorityScores.to_csv(finalPriorityScorePath, index=True, index_label='id')

        logging.info('Calculating active services from priority scores')
        activeServicesMatrix = calculateActiveServices(priorityScores)
        
        if writeActiveServicesMatrix:
            activeServicesMatrix.to_csv(finalActiveServicesMatrixPath, index=True, index_label='id')
            
        activeServicesMatrix.drop(activeServicesMatrix.columns.difference(['id', 'totalServices']), axis=1, inplace=True)
        mergedPriorityScores = priorityScores.merge(activeServicesMatrix, on='id', how='left')

        if eligibilityOptionsPath:
            logging.info('Reading eligibility options')
            if Path(eligibilityOptionsPath).suffix == '.parquet':
                logging.info('Eligibility options in parquet format, reading as such assuming RPA input')
                optionEligbilityAreas = pd.read_parquet(eligibilityOptionsPath)
                optionEligbilityAreas.set_index(polygonIdColumn, inplace=True)
                # Convert to boolean options if not already
                optionEligbility = optionEligbilityAreas.map(lambda x: False if np.isnan(x) else bool(x))
                optionEligbility.index.names = ['id']
            else:
                optionEligbilityAreas = pd.read_csv(eligibilityOptionsPath)
                optionEligbilityAreas.set_index(polygonIdColumn, inplace=True)
                optionEligbility = optionEligbilityAreas.map(lambda x: False if np.isnan(x) else bool(x))

            mergedPriorityScores = mergeEligibilityOptions(mergedPriorityScores, optionEligbility)

        logging.info('Aggregating group columns in priority scores')
        if columnGroupConfigPath:
            with open(columnGroupConfigPath) as config:
                columnGroupConfig = json.load(config)
            
            for columnGroup in columnGroupConfig.keys():
                logging.info(f'Aggregating column group {columnGroup}')
                mergedPriorityScores = groupColumnAggregation(mergedPriorityScores, columnGroup, columnGroupConfig[columnGroup]['options'], columnGroupConfig[columnGroup]['operation'])

        logging.info('Initial Priority Score Weighting')
        weightedPriorityScores = calculateInitialPriorityScoreWeighting(mergedPriorityScores)

        logging.info('Calculating weighted priority scores')
        if (Path(finalWeightedPriorityScorePath).exists()):
            if overwriteWeightedPriorityScores:
                logging.warning(f'Output path {finalWeightedPriorityScorePath} already exists, overwriting')
            else:
                raise FileExistsError(f'Output path {finalWeightedPriorityScorePath} already exists, use --overwrite-weighted-priority-scores to overwrite')

        with open(weightingsConfig) as f:
            weightings = json.load(f)
            if not set(weightings.keys()).issuperset(weightedPriorityScores.keys().to_list()):
                raise ValueError('Mismatch between priority layers and weightings')

        weightedPriorityScores = calculatePriorityScoreWeighting(weightedPriorityScores, weightings)
        weightedPriorityScores.to_csv(finalWeightedPriorityScorePath)
        

    logging.info('Calculate action scores using priorities and QEIA')
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia)

    if Path(finalMcdaPath).exists() and not overwriteMcda:
        raise FileExistsError(f'Output path {finalMcdaPath} already exists, use --overwrite-mcda to overwrite')
    
    mcda.to_csv(finalMcdaPath)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate action scores for a set of input polygons using priority scores, eligibility options and a QEIA matrix')
    parser.add_argument('-i', '--polygon-source', type=str, required=True, help='Unique ID for the polygon')
    parser.add_argument('-c', '--polygon-id-column', type=str, required=False, default='id_parcel', help='Column name for the polygon ID')
    parser.add_argument('-l', '--layer-config', type=str, required=False, default='layers.json', help='JSON file containing priority layers')
    parser.add_argument('-w', '--weightings-config', type=str, required=False, default='weightings.json', help='JSON file containing priority weightings')
    parser.add_argument('-q', '--qeia-matrix', type=str, required=False, help='Raw QEIA impact score matrix file')
    parser.add_argument('--use-precalculated-priority-scores', required=False, help='Use precalculated priority scores table as a CSV', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--priority-score-filename', type=str, required=False, help='Filename for priority scores table as CSV for this run', default='priority_scores.csv')
    parser.add_argument('--overwrite-priority-scores', required=False, help='Overwrite existing priority scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-priority-score-path', type=str, required=False, help='Full path to an optional file for priority scores as CSV', default=None)
    parser.add_argument('--use-precalculated-weighted-priority-scores', required=False, help='Use precalculated weighted priority scores table as a CSV', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--weighted-priority-score-filename', type=str, required=False, help='Filename for weighted prioirity scores table as CSV for this run', default='weighted_priority_scores.csv')
    parser.add_argument('--overwrite-weighted-priority-scores', required=False, help='Overwrite existing weigthed prioirity scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-weighted-priority-score-path', type=str, required=False, help='Full path to an optional file for weighted priority scores as CSV', default=None)
    parser.add_argument('--active-services-matrix-filename', type=str, required=False, help='Filename for active services matrix as CSV for this run, if blank dont write', default='active_services.csv')
    parser.add_argument('--write-active-services-matrix', required=False, help='Whether to write the active services matrix to a CSV file', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-active-services-matrix-path', type=str, required=False, help='Full path to an optional file for active services matrix as CSV', default=None)
    parser.add_argument('--eligibility-options-path', type=str, required=False, help='Path to eligibility options file as CSV or Parquet', default='eligibility_options.csv')
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
        args.eligibility_options_path,
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
