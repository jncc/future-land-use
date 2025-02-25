from geopandas import GeoDataFrame
from pathlib import Path

import geopandas as gpd


class PriorityLayer:
    name: str
    friendlyName: str
    path: Path
    dataTable: float
    weighting: float
    
    def __init__(self, name: str, friendlyName: str, path: Path, weighting: float):
        self.name = name
        self.friendlyName = friendlyName,

        self.weighting = weighting

        if path.exists():
            self.path = path
            self.dataTable = self.openLayer()
        else:
            raise FileNotFoundError(f'Input path ({path}) for layer "{name}" does not exist or is not accessible')
    
    def openLayer(self) -> GeoDataFrame:
        return gpd.read_file(self.path)

def processPriorityLayers(priorityLayersConfig: any, basePath: str) -> list[PriorityLayer]:
    priorityLayers: list[PriorityLayer] = []
    
    for layer in priorityLayersConfig:
        priorityLayers.append(
            PriorityLayer(
                layer, 
                priorityLayersConfig[layer]['layer_name'],
                Path(basePath).joinpath(Path(priorityLayersConfig[layer]['filename'])),
                priorityLayersConfig[layer]['weighting']
            )
        ) 

    return priorityLayers