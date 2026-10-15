import json
import argparse
import logging
from common.helpers import ConditionalFormatter, get_output_path, get_output_filename
from common.layers import PriorityLayer, processPriorityLayers
from common.timing import startTimers, endTimers
from datetime import datetime
from priority_scores import extractPriorityScoresForInputPolygons, extractPercentagesForInputPolygons
from pathlib import Path

loggingFormatStr = '%(levelname)s: %(asctime)s: %(message)s'
logging.basicConfig(
    level = logging.INFO, 
    format = loggingFormatStr
)

def main(polygonPath: str,
         polygonIdColumn: str,
         layerConfig: str,
         calculatepercentages: bool,
         priorityScoreFilename: str,
         overwritePriorityScores: bool,
         overridePriorityScorePath: str,
         outputPath: str,
         runName: str):
    '''Process a set of input polygons by extracting values from a series of 'priority' layers that overlap the input polygons.
    This can be used to extract % overlaps of different classes within layers or single scores from those layers using a range of statistics (e.g. mean/max)
    Output is a csv containing polygon IDs and statistics for each input layer in long format. 

    Args:
        polygonPath (str): Path to vector input file containing the input polygons, should support most vector formats
        polygonIdColumn (str): The name of the ID column in the input vector file
        layerConfig (str): Path to a JSON file containing a configuration object for priority layers 
        calculatepercentages (bool): If true, percentage coverage values will be extracted per class instead of maximum priority score touching parcel
        priorityScoreFilename (str): Filename for priority scores CSV file, this file will be written to / read from the output path directory
        overwritePriorityScores (bool): Overwrite priority scores file if it already exists
        overridePriorityScorePath (str): Override full path for priority scores file as CSV, None if not used
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

    with open(layerConfig) as f:
        config = json.load(f)

    (startWallTime, startProcessTime) = startTimers()
        
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate action scores for a set of input polygons using priority scores, eligibility options and a QEIA matrix')
    parser.add_argument('-i', '--polygon-source', type=str, required=True, help='Unique ID for the polygon')
    parser.add_argument('-c', '--polygon-id-column', type=str, required=False, default='NGC', help='Column name for the polygon ID')
    parser.add_argument('-l', '--layer-config', type=str, required=False, default='layers.json', help='JSON file containing priority and eligibility layers')
    parser.add_argument('--calculatepercentages', required=False, help='If true, percentage coverage values will be extracted per class instead of maximum priority score touching parcel', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--priority-score-filename', type=str, required=False, help='Filename for priority scores table as CSV for this run', default='priority_scores.csv')
    parser.add_argument('--overwrite-priority-scores', required=False, help='Overwrite existing prioirity scores table if it exists', default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('--override-priority-score-path', type=str, required=False, help='Full path to an optional file for priority scores as CSV', default=None)
    parser.add_argument('--output-path', type=str, required=True, help='Base output path to store results in')
    parser.add_argument('--run-name', type=str, required=False, help='Optional run name to append to output file pre suffix', default=None)

    args = parser.parse_args()

    main(
        args.polygon_source, 
        args.polygon_id_column, 
        args.layer_config, 
        args.calculatepercentages,
        args.priority_score_filename, 
        args.overwrite_priority_scores, 
        args.override_priority_score_path,
        args.output_path,
        args.run_name
    )
