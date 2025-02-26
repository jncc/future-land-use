from common.layers import PriorityLayer
from common.Timing import startTimers, endTimers
from shapely import Polygon
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

class Calculator:
    basePath: str
    priorityLayers: dict[str, PriorityLayer]

    def __init__(self, priorityLayers: dict[str, PriorityLayer], basePath: str = ''):
        self.basePath = basePath
        self.priorityLayers = priorityLayers

    def calculatePriorityScoreForPolygon(self, polygon: Polygon) -> dict[str, np.floating]:
        df: dict[str, np.floating] = {}
        
        for layer in self.priorityLayers:
            (startWallTime, startProcessTime) = startTimers()

            df[layer] = self.priorityLayers[layer].calculateScore(polygon)

            (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

            logging.info(f'Processed priority layer: {self.priorityLayers[layer].name}')
            logging.info(f'Wall Time: {wallTime} milliseconds')
            logging.info(f'Process Time: {processTime} milliseconds')

        return df

