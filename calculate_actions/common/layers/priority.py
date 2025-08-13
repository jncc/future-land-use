from common.layers import RasterLayer, VectorLayer
from shapely import Polygon
from pathlib import Path
import numpy as np
from rasterstats import zonal_stats

class PriorityLayer:
    """Base class for Priority Layers, to be overidden by vector or raster implementations
    as appropriate
    """

    def __init__(self):
        """Creates a holding base class, sets the weighting for this layer
        """
        pass

    def extractScore(self, polygon: Polygon) -> np.floating:
        """Calculate the score of this layer against a supplied polygon

        Args:
            polygon (Polygon): The Polygon to intersect this layer with

        Raises:
            NotImplementedError: Not implemented in this base class

        Returns:
            np.floating: Returns the maxium score for this layer and a supplied polygon
        """
        raise NotImplementedError('calculateScore function is not implemented in PriorityLayer class')

class PriorityVectorLayer(VectorLayer, PriorityLayer):   
    """Class for Vector based Priority Layers, extends the VectorLayer and PriorityLayer
    classes for functionality and prototyping
    """
    columnName: str

    def __init__(self, name: str, friendlyName: str, path: Path, columnName: str = 'PriorityScore'):
        """Initialises the VectorLayer and PriorityLayer superclasses with the supplied
        values

        Args:
            name (str): A computer friendly name for this layer
            friendlyName (str): A human friendly anme for this layer
            path (Path): The fully path to the vector layer file
            columnName (str, optional): The score column to use from the vector layer. Defaults to 'PriorityScore'.
        """
        VectorLayer.__init__(self, name, friendlyName, path)
        PriorityLayer.__init__(self)
        self.columnName = columnName
    
    def extractScore(self, polygon: Polygon) -> np.floating:
        """Calculates the score for this layer intersected with the input Polygon, takes the maximum
        score value from the columnName column that intersects, ignoring ones where there is only a touch at the boundary. 

        Args:
            polygon (Polygon): A polygon to intersect this layer with
            columnName (str, optional): The score column to use from the vector layer. Defaults to 'PriorityScore'.

        Returns:
            np.floating: The maximum score for this layer intersected with the input polygon
        """

        intersectingPolygons = self.dataTable.intersects(polygon)
        touchingPolygons = self.dataTable.touches(polygon)
        intersectsNotTouches = self.dataTable[intersectingPolygons & ~touchingPolygons]
        return intersectsNotTouches[self.columnName].max()

class PriorityRasterLayer(RasterLayer, PriorityLayer):
    """Class for Raster based Priority Layers, extends the RasterLayer and PriorityLayer
    classes for functionality and prototyping.
    """

    def __init__(self, name: str, friendlyName: str, path: Path):
        """Initialises the RasterLayer and PriorityLayer superclasses with the supplied
        values

        Args:
            name (str): A computer friendly name for this layer
            friendlyName (str): A human friendly anme for this layer
            path (Path): The fully path to the vector layer file
            weighting (float, optional): The weighting for this prioirity layer. Defaults to 1.
        """
        RasterLayer.__init__(self, name, friendlyName, path)
        PriorityLayer.__init__(self)

    def extractScore(self, polygon: Polygon) -> np.floating:
        """Calculates the score for this layer interescted with the input Polygon, takes the maximum
        score value from the input raster via zonal stats

        Args:
            polygon (Polygon): A polygon to intersect this layer with

        Returns:
            np.floating: The maximum score for this layer intersected with the input polygon
        """

        stats = zonal_stats(
            polygon,
            str(self.path),
            stats=["max"],
        )

        if stats and stats[0] and 'max' in stats[0] and stats[0]['max'] is not None:
            return np.float64(stats[0]['max'])
        else:
            return np.float64(np.nan)


def processPriorityLayers(priorityLayersConfig: dict[str, dict[str, str]]) -> dict[str, PriorityLayer]:
    """Process and open a list of priority layers, as vector or raster layers as appropriate,
    currently only vector layers are supported, inputs should be of the form;
    {
        "drought": {
            "layer_name": "Drought",
            "filename": "Drought.gpkg",
            "weighting": 1.23
        },
        ...
    }

    Args:
        priorityLayersConfig (dict[str, dict[str, str]]): Input dict object containing config information
        for all priority layers in this service

    Returns:
        dict[str, PriorityLayer]: A dict containing configured PriorityLayer objects ready to intersect
        with inputs
    """
    priorityLayers: dict[str, PriorityLayer] = {}
    
    for layer in priorityLayersConfig:
        if priorityLayersConfig[layer]['type'] == 'vector':
            if 'column_name' in priorityLayersConfig[layer]:
                priorityLayers[layer] = PriorityVectorLayer(
                        layer, 
                        priorityLayersConfig[layer]['layer_name'],
                        Path(priorityLayersConfig[layer]['filepath']),
                        priorityLayersConfig[layer]['column_name']
                    )
            else:
                priorityLayers[layer] = PriorityVectorLayer(
                        layer, 
                        priorityLayersConfig[layer]['layer_name'],
                        Path(priorityLayersConfig[layer]['filepath'])
                    )
        elif priorityLayersConfig[layer]['type'] == 'raster':
            priorityLayers[layer] = PriorityRasterLayer(
                layer, 
                priorityLayersConfig[layer]['layer_name'],
                Path(priorityLayersConfig[layer]['filepath'])
            )                

    return priorityLayers