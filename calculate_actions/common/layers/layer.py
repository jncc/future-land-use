from pathlib import Path
from io import TextIOWrapper

class Layer:
    """Contains common config elements and functions for all layers, designed to be used
    as a container class for priority and eligbility layers
    """
    name: str
    friendlyName: str
    path: Path
    
    def __init__(self, name: str, friendlyName: str, path: Path):
        """Sets the name, friendlyName and path elements of the layer, the path must
        exist on the filesystem

        Args:
            name (str): A computer friendly name for this layer
            friendlyName (str): A human friendly name for this layer
            path (Path): The path the the file object for this layer

        Raises:
            FileNotFoundError: If the path does not exist on the filesystem
        """
        self.name = name
        self.friendlyName = friendlyName,

        if path.exists():
            self.path = path
        else:
            raise FileNotFoundError(f'Input path ({path}) for layer "{name}" does not exist or is not accessible')
        
    def openLayer(self):
        """Unimplemented function designed to be overriden by vector or raster 
        classes, call to open the file/data object for this layer

        Raises:
            NotImplementedError: Should not call the super class version of this function
        """
        raise NotImplementedError('openLayer not implemented in base Layer class')

    def closeLayer(self):
        """Unimplemented function designed to be overriden by vector or raster 
        classes, call to close the file/data object for this layer

        Raises:
            NotImplementedError: Should not call the super class version of this function
        """
        raise NotImplementedError('closeLayer not implemented in base Layer class')

from geopandas import GeoDataFrame
import geopandas as gpd

class VectorLayer(Layer):
    """A Layer class designed to open and interact with vector data sources on the local
    filesystem
    """
    dataTable: GeoDataFrame
    
    def __init__(self, name: str, friendlyName: str, path: Path):
        """Initialises superclass and opens the current vector layer with geopandas for 
        comparison operations

        Args:
            name (str): A computer friendly name for this layer
            friendlyName (str): A human friendly name for this layer
            path (Path): The path the the file object for this layer

        Raises:
            FileNotFoundError: If the path does not exist on the filesystem
        """
        super().__init__(name, friendlyName, path)
        self.dataTable = self.openLayer()
    
    def openLayer(self) -> GeoDataFrame:
        """Opens the current vector layer and reads its contents into a GeoDataFrame

        Returns:
            GeoDataFrame: A GeoPandas Dataframe with the contents of this vector layer
        """
        return gpd.read_file(self.path)
    
    def closeLayer(self):
        """Closes the current vector layer, unassigns the dataframe to free up the object
        """
        self.dataTable = None

class RasterLayer(Layer):
    """A Layer class designed to open and interact with raster data sources on the local
    filesystem
    """
    filePointer: TextIOWrapper = None

    def __init__(self, name, friendlyName, path):
        """Initialises superclass and opens the current raster layer and returns a file
        pointer object for use with raster processing libraries

        Args:
            name (str): A computer friendly name for this layer
            friendlyName (str): A human friendly name for this layer
            path (Path): The path the the file object for this layer

        Raises:
            FileNotFoundError: If the path does not exist on the filesystem
        """
        super().__init__(name, friendlyName, path)
    
    def openLayer(self) -> TextIOWrapper:
        """Opens the layer and returns the file pointer for use with comparison 
        operations

        Returns:
            TextIOWrapper: File pointer for this layer
        """
        self.filePointer = open(self.path)
    
    def closeLayer(self):
        """Closes the filepointer for this layer
        """
        self.filePointer.close()
    