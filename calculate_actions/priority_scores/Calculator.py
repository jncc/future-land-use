from common.PriorityLayer import PriorityLayer
from common.Timing import startTimers, endTimers
from shapely import Polygon
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

class Calculator:
    basePath: str
    priorityLayers: list[PriorityLayer]

    def __init__(self, priorityLayers: list[PriorityLayer], basePath: str = ''):
        self.basePath = basePath
        self.priorityLayers = priorityLayers

    def calculatePriorityScoreForPolygon(self, polygon: Polygon):
        df = []
        
        for layer in self.priorityLayers:
            (startWallTime, startProcessTime) = startTimers()

            intersectingPolygons = layer.dataTable.intersects(polygon)
            df.append((layer.name, (layer.dataTable.join(intersectingPolygons.rename('intersecting')))[lambda x: x['intersecting']]['PriorityScore'].max()))

            (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

            logging.info(f'Processed priority layer: {layer.name}')
            logging.info(f'Wall Time: {wallTime} milliseconds')
            logging.info(f'Process Time: {processTime} milliseconds')
            


        return df

