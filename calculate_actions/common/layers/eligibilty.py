from common.layers import VectorLayer, RasterLayer
from pathlib import Path
from shapely import Polygon

class EligibilityLayer:
    def __init__(self):
        pass
    
    def discoverEligibility(self, polygon: Polygon, columnName: str = 'Eligible') -> bool:
        raise NotImplementedError('calculateEligibility not implemented on EligibilityLayer class')

class EligibilityVectorLayer(VectorLayer, EligibilityLayer):
    def __init__(self, name, friendlyName, path):
        super(EligibilityVectorLayer, self).__init__(name, friendlyName, path)
    
    def discoverEligibility(self, polygon, columnName = 'Eligible') -> bool:
        return True

class EligibilityRasterLayer(RasterLayer, EligibilityLayer):
    def __init__(self, name, friendlyName, path):
        super(EligibilityRasterLayer, self).__init__(name, friendlyName, path)
    
    def discoverEligibility(self, polygon, columnName = 'Eligible') -> bool:
        return True

def processEligibilityLayers(eligibilityLayersConfig: any, basePath: str) -> list[EligibilityLayer]:
    eligibilityLayers: list[EligibilityLayer] = []
    
    for layer in eligibilityLayersConfig:
        eligibilityLayers.append(
            EligibilityVectorLayer(
                layer, 
                eligibilityLayersConfig[layer]['layer_name'],
                Path(basePath).joinpath(Path(eligibilityLayersConfig[layer]['filename']))
            )
        ) 

    return eligibilityLayers