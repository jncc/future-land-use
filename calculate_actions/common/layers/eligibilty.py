from common.layers import VectorLayer, RasterLayer, Layer
from pathlib import Path
from shapely import Polygon

class EligibilityLayer:
    """Base class for Eligibility Layers, to be overidden by vector or raster implementations
    as appropriate
    """
    layer: Layer

    def __init__(self, layer: Layer):
        """Creates a holding base class, nothing implemented here
        """
        self.layer = layer
    
    def determineEligibility(self, polygon: Polygon) -> bool:
        """Determines the eligibility of a given polygon

        Args:
            polygon (Polygon): The polygon to determine eligible options for

        Raises:
            NotImplementedError: This function has not been implemetned here, needs to be overriden

        Returns:
            bool: Returns True if this polygon intersects with any of the vector data
        """
        raise NotImplementedError('calculateEligibility not implemented on EligibilityLayer class')

class EligibilityVectorLayer(VectorLayer, EligibilityLayer):
    """Extends base EligibiltyLayer class for functionality with vector input layers
    """

    def __init__(self, name: str , friendlyName: str, path: str):
        """Creates the multi superclasses involved with this, a VectorLayer and
        an EligibilityLayer

        Args:
            name (str): Computer friendly name for this layer
            friendlyName (str): Human friendly name for this layer
            path (str): Full path to the the input vector layer file
        """
        VectorLayer.__init__(self, name, friendlyName, path)
        EligibilityLayer.__init__(self, self)
    
    def determineEligibility(self, polygon: Polygon) -> bool:
        """Determines what are the eligible options for the provided polygon against the
        vector input

        Args:
            polygon (Polygon): The polygon to determine eligible options for

        Returns:
            bool: Returns True if this polygon intersects with any of the vector data
        """
        intersectingPolygons = self.dataTable.intersects(polygon)

        if (self.dataTable.join(intersectingPolygons.rename('intersecting')))[lambda x: x['intersecting']].shape[0] > 0:
            return True
        return False

class EligibilityRasterLayer(RasterLayer, EligibilityLayer):
    """Extends base EligibiltyLayer class for functionality with raster input layers
    """

    def __init__(self, name, friendlyName, path):
        """Creates the multi superclasses involved with this, a RasterLayer and
        an EligibilityLayer

        Args:
            name (str): Computer friendly name for this layer
            friendlyName (str): Human friendly name for this layer
            path (str): Full path to the the input vector layer file
        """
        RasterLayer.__init__(self, name, friendlyName, path)
        EligibilityLayer.__init__(self)
    
    def determineEligibility(self, polygon: Polygon) -> bool:
        """Determines what are the eligible options for the provided polygon against the
        raster input

        Args:
            polygon (Polygon): The polygon to determine eligible options for

        Returns:
            bool: Returns True if this polygon intersects with any of the vector data
        """
        return True

def processEligibilityLayers(eligibilityLayersConfig: dict[str, dict[str, str]]) -> dict[str, EligibilityLayer]:
    """Process an input config object (JSON) into a dict of EligiblityLayers, automatically
    creating the appropriate Vector or Raster layer underneath

    Args:
        eligibilityLayersConfig (dict[str, dict[str, str]]): Input config dict of the form
        {
            "gs67": {
                "layer_name": "GS67",
                "filepath": "footprint_GS67.gpkg"
        },
        "lh1": {
            "layer_name": "LH1",
            "filepath": "footprint_LH1.gpkg"
        },
        ...

    Returns:
        dict[str, EligibilityLayer]: A dict of all eligibility layers ready to use
    """
    eligibilityLayers: dict[str, EligibilityLayer] = {}
    
    for layer in eligibilityLayersConfig:
        eligibilityLayers[layer] = EligibilityVectorLayer(
                layer, 
                eligibilityLayersConfig[layer]['layer_name'],
                Path(eligibilityLayersConfig[layer]['filepath']))

    return eligibilityLayers