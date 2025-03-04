from pathlib import Path
from io import TextIOWrapper

class Layer:
    name: str
    friendlyName: str
    path: Path
    
    def __init__(self, name: str, friendlyName: str, path: Path):
        self.name = name
        self.friendlyName = friendlyName,

        if path.exists():
            self.path = path
        else:
            raise FileNotFoundError(f'Input path ({path}) for layer "{name}" does not exist or is not accessible')
        
    def openLayer(self):
        raise NotImplementedError('openLayer not implemented in base Layer class')

    def closeLayer(self):
        raise NotImplementedError('closeLayer not implemented in base Layer class')

from geopandas import GeoDataFrame
import geopandas as gpd

class VectorLayer(Layer):
    dataTable: GeoDataFrame
    
    def __init__(self, name: str, friendlyName: str, path: Path):
        super().__init__(name, friendlyName, path)
        self.dataTable = self.openLayer()
    
    def openLayer(self) -> GeoDataFrame:
        return gpd.read_file(self.path)
    
    def closeLayer(self):
        self.dataTable = None

class RasterLayer(Layer):
    filePointer: TextIOWrapper = None

    def __init__(self, name, friendlyName, path):
        super().__init__(name, friendlyName, path)
    
    def openLayer(self):
        self.filePointer = open(self.path)
    
    def closeLayer(self):
        self.filePointer.close()
    