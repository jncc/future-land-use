from common.layers import RasterLayer, VectorLayer
from shapely import Polygon
from pathlib import Path
import numpy as np

class PriorityLayer:
    weighting: float

    def __init__(self, weighting: float):
        self.weighting = weighting

    def calculateScore(self, polygon: Polygon, columnName: str = 'PriorityScore') -> np.floating:
        raise NotImplementedError('calculateScore function is not implemented in PriorityLayer class')
    
    def calculateWeightedScore(self, score: np.floating, decimalPlaces: int = 2) -> np.floating:
        return np.round(np.float64(score * self.weighting), decimalPlaces)

class PriorityVectorLayer(VectorLayer, PriorityLayer):   
    def __init__(self, name: str, friendlyName: str, path: Path, weighting: float = 1):
        VectorLayer.__init__(self, name, friendlyName, path)
        PriorityLayer.__init__(self, weighting)
    
    def calculateScore(self, polygon: Polygon, columnName: str = 'PriorityScore') -> np.floating:
        intersectingPolygons = self.dataTable.intersects(polygon)
        return (self.dataTable.join(intersectingPolygons.rename('intersecting')))[lambda x: x['intersecting']][columnName].max()

class PriorityRasterLayer(RasterLayer, PriorityLayer):   
    def __init__(self, name: str, friendlyName: str, path: Path, weighting: float):
        super(PriorityRasterLayer).__init__(name, friendlyName, path, weighting)

    def calculateScore(self, polygon: Polygon, columnName: str = 'PriorityScore'):
        return super().calculateScore(polygon, columnName)

def processPriorityLayers(priorityLayersConfig: any) -> dict[str, PriorityLayer]:
    priorityLayers: dict[str, PriorityLayer] = {}
    
    for layer in priorityLayersConfig:
        priorityLayers[layer] = PriorityVectorLayer(
                layer, 
                priorityLayersConfig[layer]['layer_name'],
                Path(priorityLayersConfig[layer]['filename']),
                priorityLayersConfig[layer]['weighting']
            )

    return priorityLayers