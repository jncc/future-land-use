from common.layers import EligibilityLayer
from common.timing import startTimers, endTimers
from shapely import Polygon

import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

class Calculator:
    basePath: str
    eligibilityLayer: dict[str, EligibilityLayer]

    def __init__(self, eligibilityLayer: dict[str, EligibilityLayer], basePath: str = ''):
        self.basePath = basePath
        self.eligibilityLayer = eligibilityLayer

    def determineEligibilityForPolygon(self, polygon: Polygon) -> list[str]:
        df: set[str] = set([])
        
        for layer in self.eligibilityLayer:
            (startWallTime, startProcessTime) = startTimers()

            (eligible, options) = self.eligibilityLayer[layer].determineEligibility(polygon)
            if eligible:
                for option in options:
                    df.add(option)

            (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

            logging.info(f'--- Processed eligibility layer: {self.eligibilityLayer[layer].name}')
            logging.info(f'--- Wall Time: {wallTime} milliseconds')
            logging.info(f'--- Process Time: {processTime} milliseconds')

        return list(df)

    def createOutputTableRow(self, id, options, eligibleOptions):
        row = {'id': [id]}
        
        for option in options:
            row[option] = [option in eligibleOptions]

        return pd.DataFrame.from_dict(row)