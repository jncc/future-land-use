from common.layers import VectorLayer, RasterLayer
from pathlib import Path
from shapely import Polygon

import numpy as np

class EligibilityLayer:
    def __init__(self):
        pass
    
    def determineEligibility(self, polygon: Polygon, nameColumn: str = 'Option') -> tuple[bool, np.ndarray[str]]:
        raise NotImplementedError('calculateEligibility not implemented on EligibilityLayer class')

class EligibilityVectorLayer(VectorLayer, EligibilityLayer):
    def __init__(self, name, friendlyName, path):
        super(EligibilityVectorLayer, self).__init__(name, friendlyName, path)
    
    def determineEligibility(self, polygon: Polygon,  nameColumn: str = 'option') -> tuple[bool, np.ndarray[str]]:
        intersectingPolygons = self.dataTable.intersects(polygon)

        if (self.dataTable.join(intersectingPolygons.rename('intersecting')))[lambda x: x['intersecting']].shape[0] > 0:
            return (True, (self.dataTable.join(intersectingPolygons.rename('intersecting')))[lambda x: x['intersecting']][nameColumn].unique())
        return (False, None)

class EligibilityRasterLayer(RasterLayer, EligibilityLayer):
    def __init__(self, name, friendlyName, path):
        super(EligibilityRasterLayer, self).__init__(name, friendlyName, path)
    
    def determineEligibility(self, polygon: Polygon,  nameColumn: str = 'Option') -> tuple[bool, np.ndarray[str]]:
        return True

def processEligibilityLayers(eligibilityLayersConfig: any) -> dict[str, EligibilityLayer]:
    eligibilityLayers: dict[str, EligibilityLayer] = {}
    
    for layer in eligibilityLayersConfig:
        eligibilityLayers[layer] = EligibilityVectorLayer(
                layer, 
                eligibilityLayersConfig[layer]['layer_name'],
                Path(eligibilityLayersConfig[layer]['filename']))

    return eligibilityLayers