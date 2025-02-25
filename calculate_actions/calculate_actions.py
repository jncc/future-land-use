import os
import json
import argparse
import logging
import shapely
import geopandas as gpd

from shapely import to_wkt

from common.PriorityLayer import PriorityLayer, processPriorityLayers
from priority_scores.Calculator import Calculator as PriorityCalculator
from priority_scores.Weighting import Weighting as PriorityWeighting

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

def get_weighted_priority_score(poly_id, priority_score, weightings):
    return 0

def get_eligibility(polygon, eligibility_filepath):
    return False

def get_qeia_scores(option, qeia_matrix):
    return {}

def get_action_scores(option, priority_scores):
    return 0

def main(poly_id, wkt, data_dir, layer_config, priority_weightings, qeia_matrix):
    logging.info(f'Generating actions for polygon {poly_id} defined in {wkt}')

    priorityLayers: list[PriorityLayer] = []
    eligibility_layers = {}
    with open(layer_config) as f:
        config = json.load(f)
        priorityLayers = processPriorityLayers(config['priority_layers'], data_dir)
        eligibility_layers = config['eligibility_layers']

    logging.info(f'Found {len(priorityLayers)} priority layers in the config file')

    polygon = ''
    with open(wkt) as f:
        polygon = f.readline()

    logging.info(f'Input polygon: {polygon}')

    logging.info('Calculate priority scores')
    priorityCalculator = PriorityCalculator(priorityLayers, data_dir)
    priorityScores = priorityCalculator.calculatePriorityScoreForPolygon(shapely.from_wkt(geometry=polygon))
    print(priorityScores)

    logging.info('Calculating weighted priority scores')
    priorityWeightingCalculator = PriorityWeighting(priorityLayers)
    weightedPriorityScores = priorityWeightingCalculator.calculateWeightings(priorityScores)
    print(weightedPriorityScores)

    logging.info("Filter QEIA scores for polygon")
    qeia_scores = {}
    for eligibility_layer in eligibility_layers:
        option = eligibility_layer["layer_name"]
        filename = eligibility_layer["filename"]

        eligible = get_eligibility(polygon, filename)

        if eligible:
            filtered_qeia = get_qeia_scores(option, qeia_matrix)
    
            qeia_scores[option] = filtered_qeia

    logging.info("Calculate action scores using priorities and filtered QEIA")
    action_scores = {}
    for option in qeia_scores.keys():
        option_score = get_action_scores(option, priorityScores)

        action_scores[option] = option_score

    # save action_scores to file or something?

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate action scores for a given polygon land parcel")
    parser.add_argument('-i', '--poly_id', type=str, required=True, help="Unique ID for the polygon")
    parser.add_argument('-w', '--wkt', type=str, required=True, help="WKT file containing polygon geometry")
    parser.add_argument('-d', '--data_dir', type=str, required=True, help="Directory containing all the layers")
    parser.add_argument('-l', '--layer_config', type=str, required=False, default="layers.json", help="JSON file containing priority and eligibility layers")
    parser.add_argument('-p', '--priority_weightings', type=str, required=True, help="File containing priority weightings matrix")
    parser.add_argument('-q', '--qeia_matrix', type=str, required=False, help="Raw QEIA impact score matrix file")

    args = parser.parse_args()

    main(args.poly_id, args.wkt, args.data_dir, args.layer_config, args.priority_weightings, args.qeia_matrix)