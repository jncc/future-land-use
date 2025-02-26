from pathlib import Path

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

from geopandas import GeoDataFrame
import geopandas as gpd

class VectorLayer(Layer):
    dataTable: GeoDataFrame
    
    def __init__(self, name: str, friendlyName: str, path: Path):
        super().__init__(name, friendlyName, path)
        self.dataTable = self.openLayer()
    
    def openLayer(self) -> GeoDataFrame:
        return gpd.read_file(self.path)

class RasterLayer(Layer):
    def __init__(self, name, friendlyName, path):
        super().__init__(name, friendlyName, path)