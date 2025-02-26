from common.layers import PriorityLayer
from shapely import Polygon

class Calculator:
    basePath: str
    priorityLayers: list[PriorityLayer]

    def __init__(self, priorityLayers: list[PriorityLayer], basePath: str = ''):
        self.basePath = basePath
        self.priorityLayers = priorityLayers

    def calculate(self, polygon: Polygon):
        pass

