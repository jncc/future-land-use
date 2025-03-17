import json
import argparse
import logging
import shapely

from common.layers import EligibilityLayer, PriorityLayer, processEligibilityLayers, processPriorityLayers
from common.timing import startTimers, endTimers
from common.qeia import QEIAMatrix
from priority_scores import Calculator as PriorityCalculator, Weighting as PriorityWeighting
from eligibility import Calculator as EligibilityCalculator
from mcda import calculateMultiCriteriaDecisionAnalysisForParcel, calculateMCDAForPriorityScoresWithEligibility
from pathlib import Path
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

def calculatePriorityScoresForInputPolygons(polygonSource: Path, prioirityLayers: dict[str, PriorityLayer]) -> pd.DataFrame:
    """Calculate the priority scores for the input polygon, using the provided priority layers

    Args:
        polygonSource (Path): A path to a WKT file containing the input polygon
        prioirityLayers (dict[str, PriorityLayer]): A dictionary containing the priority layers to use in the calculation

    Returns:
        pd.DataFrame: A DataFrame containing the priority scores for the input polygon
    """
    inputParcels = gpd.read_file(polygonSource)
    priorityCalculator = PriorityCalculator(prioirityLayers)
    inputPriorityScores = pd.DataFrame(columns=prioirityLayers.keys())
    print(inputParcels)

    for parcel in inputParcels.iterrows():
        inputPriorityScores.loc[parcel[1]['NGC']] = priorityCalculator.calculatePriorityScoreForPolygonAsArray(parcel[1]['geometry'], False)        

    return inputPriorityScores

def calculateWeightedPriorityScoresForInputPolygons(priorityScores: pd.DataFrame, priorityLayers: dict[str, PriorityLayer]) -> pd.DataFrame:
    for priorityLayer in priorityLayers:
        priorityScores[priorityLayer] = priorityScores[priorityLayer].apply(lambda x: x * priorityLayers[priorityLayer].weighting)

    return priorityScores

def calculateOptionEligibilityForInputPolygons(polygonSource: Path, eligibilityLayers: dict[str, EligibilityLayer]) -> pd.DataFrame:
    """Calculate the eligibility for the input polygon, using the provided eligibility layers
    """
    inputParcels = gpd.read_file(polygonSource)
    eligibilityCalculator = EligibilityCalculator(eligibilityLayers)
    inputEligibility = pd.DataFrame(columns=eligibilityLayers.keys())

    for parcel in inputParcels.iterrows():
        eligibleLayers = eligibilityCalculator.determineEligibilityForPolygon(parcel[1]['geometry'], False)
        inputEligibility.loc[parcel[1]['NGC']] = [True if eligibilityLayers[layer].layer.name in eligibleLayers else False for layer in eligibilityLayers.keys()]

    return inputEligibility

# def eligibilityTableToMCDAEligibilityTemplate(eligibilityTable: pd.DataFrame) -> pd.DataFrame:
#     eligbilitySeries = eligibilityTable.agg(lambda x: [col for i, col in enumerate(eligibilityTable.columns) if x.iloc[i]], axis=1)
#     return pd.DataFrame(eligbilitySeries.explode(), index=eligibilityTable.index, columns=['option']).reset_index()

# def eligibilityTemplateToQEIAMultiplier(eligibilityTemplate: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
#     return eligibilityTemplate.merge(qeia.createOutputTableRow().transpose(), on='option').set_index(['id', 'option'])

# def mcdaOutput(priorityScores: pd.DataFrame, qeia: QEIAMatrix, eligibility: pd.DataFrame) -> pd.DataFrame:
#     template = eligibilityTableToMCDAEligibilityTemplate(eligibility)
#     qeiaMultiplier = eligibilityTemplateToQEIAMultiplier(template, qeia)
#     mcda = priorityScores.merge(template, on='id').set_index(['id', 'option'])
#     mcda = mcda.multiply(qeiaMultiplier)
#     mcda['total'] = mcda.sum(axis=1)
#     mcda['rank'] = mcda.groupby(level=0)['total'].rank(method='first', ascending=False)

#     return mcda.sort_values(['id', 'rank'])
    
def main(polygonPath: str,
         polygonIdColumn: str,
         layerConfig: str,
         qeiaMatrix: str,
         precalculatedPriorityScores: str,
         priorityScoreOutputPath: str,
         overwritePriorityScores: bool,
         precalculatedWeightedPrioirityScores: str,
         weightedPriorityScoreOutputPath: str,
         overwriteWeightedPriorityScores: bool,
         precalculatedEligibility: str, 
         eligibilityScoreOutputPath: str, 
         overwriteEligibilityScores: bool):
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
        logging.info('Calculating priority scores')
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
            priorityScores = calculatePriorityScoresForInputPolygons(Path(polygonPath), priorityLayers)
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
            
        weightedPriorityScores = calculateWeightedPriorityScoresForInputPolygons(priorityScores, priorityLayers)
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

    # logging.info("Filter QEIA scores eligibility")
    
    # (startWallTime, startProcessTime) = startTimers()
    # filteredQeia = rawQeia.getFilteredMatrix(optionEligbility.loc[:, optionEligbility.any()].columns)
    # (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

    # logging.info('---------------------------- QEIA Filtering Complete ---------------------------- ')
    # logging.info(f'Wall Time: {wallTime} milliseconds')
    # logging.info(f'Process Time: {processTime} milliseconds')

    # print(filteredQeia.createOutputTableRow())

    logging.info("Calculate action scores using priorities and QEIA")
    (startWallTime, startProcessTime) = startTimers()
    mcda = calculateMCDAForPriorityScoresWithEligibility(weightedPriorityScores, rawQeia, optionEligbility)
    mcda.to_csv('mcda.csv')
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

    # save action_scores to file or something?

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate action scores for a given polygon land parcel")
    parser.add_argument('-i', '--poly_source', type=str, required=True, help="Unique ID for the polygon")
    parser.add_argument('-c', '--polygon_id_column', type=str, required=False, default="NGC", help="Column name for the polygon ID")
    parser.add_argument('-l', '--layer_config', type=str, required=False, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-q', '--qeia_matrix', type=str, required=False, help="Raw QEIA impact score matrix file")
    parser.add_argument('-s', '--precalculated_priority_scores', type=str, required=False, help="Optional path precalculated priority scores table as a CSV", default=None)
    parser.add_argument('--priority_score_output_path', type=str, required=False, help="Path to output prioirity scores table as CSV for this run", default="priority_scores.csv")
    parser.add_argument('--overwrite_priority_score_output', type=bool, required=False, help="Overwrite existing prioirity scores table if it exists", default=False)
    parser.add_argument('-w', '--precalculated_weighted_priority_scores', type=str, required=False, help="Optional path precalculated weighted priority scores table as a CSV", default=None)
    parser.add_argument('--weighted_priority_score_output_path', type=str, required=False, help="Path to output prioirity scores table as CSV for this run", default="weighted_priority_scores.csv")
    parser.add_argument('--overwrite_weighted_priority_score_output', type=bool, required=False, help="Overwrite existing weigthed prioirity scores table if it exists", default=False)
    parser.add_argument('-e', '--precalculated_eligibility', type=str, required=False, help="Optional path precalculated option eligiblity table as a CSV", default=None)
    parser.add_argument('--eligiblity_score_output_path', type=str, required=False, help="Path to output prioirity scores table as CSV for this run", default="eligibility.csv")
    parser.add_argument('--overwrite_eligiblity_output', type=bool, required=False, help="Overwrite existing option eligiblity table if it exists", default=False)

    args = parser.parse_args()

    main(
        args.poly_source, 
        args.polygon_id_column, 
        args.layer_config, 
        args.qeia_matrix, 
        args.precalculated_priority_scores, 
        args.priority_score_output_path, 
        args.overwrite_priority_score_output, 
        args.precalculated_weighted_priority_scores, 
        args.weighted_priority_score_output_path, 
        args.overwrite_weighted_priority_score_output, 
        args.precalculated_eligibility, 
        args.eligiblity_score_output_path, 
        args.overwrite_eligiblity_output
    )