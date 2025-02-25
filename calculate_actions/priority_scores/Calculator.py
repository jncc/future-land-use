from common.PriorityLayer import PriorityLayer
from shapely import Polygon
from pathlib import Path
import pandas as pds

class Calculator:
    basePath: str
    priorityLayers: list[PriorityLayer]

    def __init__(self, priorityLayers: list[PriorityLayer], basePath: str = ''):
        self.basePath = basePath
        self.priorityLayers = priorityLayers

    def calculatePriorityScoreForPolygon(self, polygon: Polygon):
        df = []
        
        for layer in self.priorityLayers:
            intersectingPolygons = layer.dataTable.intersects(polygon)
            df.append((layer.name, (layer.dataTable.join(intersectingPolygons.rename('intersecting')))[lambda x: x['intersecting']]['PriorityScore'].max()))

        return df

