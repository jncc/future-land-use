from common.layers import PriorityLayer
from common.timing import startTimers, endTimers
from shapely import Polygon
from pathlib import Path
import logging
import numpy as np
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

class Calculator:
    """Calculator object for priority layers, calculates a given prioirty score for a polygon
    against all supplied priority layers
    """
    priorityLayers: dict[str, PriorityLayer]

    def __init__(self, priorityLayers: dict[str, PriorityLayer]):
        """Helper class to deal with calculating the score for input polygons against an set of
        prioirity layers

        Args:
            priorityLayers (dict[str, PriorityLayer]): A dict of configured PriorityLayers to compare
            with
        """
        self.priorityLayers = priorityLayers

    def extractPriorityScoreForPolygon(self, polygon: Polygon, timing: bool = True) -> dict[str, np.floating]:
        """Calculate the priorty scores for a single polygon against a set of priority layers

        Args:
            polygon (Polygon): Input Polygon to intersect with priority layers

        Returns:
            dict[str, np.floating]: A dict of layer name / score pairs
        """
        df: dict[str, np.floating] = {}
        
        for layer in self.priorityLayers:
            if timing:
                (startWallTime, startProcessTime) = startTimers()

            df[layer] = self.priorityLayers[layer].extractScore(polygon)

            if timing:
                (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

                logging.info(f'--- Processed priority layer: {self.priorityLayers[layer].name}')
                logging.info(f'--- Wall Time: {wallTime} milliseconds')
                logging.info(f'--- Process Time: {processTime} milliseconds')

        return df

    def extractPriorityScoreForPolygonAsArray(self, polygon: Polygon, timing: bool = True) -> list[np.floating]:
        """Calculate the priorty scores for a single polygon against a set of priority layers

        Args:
            polygon (Polygon): Input Polygon to intersect with priority layers

        Returns:
            dict[str, np.floating]: A dict of layer name / score pairs
        """
        df: list[np.floating] = []
        
        for layer in self.priorityLayers:
            if timing:
                (startWallTime, startProcessTime) = startTimers()

            df.append(self.priorityLayers[layer].extractScore(polygon))

            if timing:
                (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

                logging.info(f'--- Processed priority layer: {self.priorityLayers[layer].name}')
                logging.info(f'--- Wall Time: {wallTime} milliseconds')
                logging.info(f'--- Process Time: {processTime} milliseconds')

        return df
    
def extractPriorityScoresForInputPolygon(polygonId: str, polygon: Polygon, priorityLayers: dict[str, PriorityLayer]) -> pd.DataFrame:
    """Calculate the priority scores for the input polygon, using the provided priority layers

    Args:
        polygonId (str): A unique identifier for the input polygon
        polygon (Polygon): The input polygon to calculate the priority scores for
        priorityLayers (dict[str, PriorityLayer]): A dictionary containing the priority layers to use in the calculation

    Returns:
        pd.DataFrame: A DataFrame containing the priority scores for the input polygon
    """
    priorityCalculator = Calculator(priorityLayers)
    inputPriorityScores = pd.DataFrame(columns=priorityLayers.keys())
    inputPriorityScores.index.name = 'id'

    inputPriorityScores.loc[polygonId] = priorityCalculator.extractPriorityScoreForPolygonAsArray(polygon, False)

    return inputPriorityScores

def extractPriorityScoresForInputPolygons(polygonSource: Path, priorityLayers: dict[str, PriorityLayer], polygonIdColumn: str) -> pd.DataFrame:
    """Calculate the priority scores for the input polygon, using the provided priority layers

    Args:
        polygonSource (Path): A path to a parquet or GeoPandas compatible GIS file containing the input polygons
        priorityLayers (dict[str, PriorityLayer]): A dictionary containing the priority layers to use in the calculation
        polygonIdColumn (str): The name of the column containing the unique identifier for each input polygon

    Returns:
        pd.DataFrame: A DataFrame containing the priority scores for the input polygon
    """
    if polygonSource.suffix == '.parquet':
        inputParcels = gpd.read_parquet(polygonSource)
    else:
        inputParcels = gpd.read_file(polygonSource)
    priorityCalculator = Calculator(priorityLayers)
    inputPriorityScores = pd.DataFrame(columns=priorityLayers.keys())
    inputPriorityScores.index.name = 'id'

    for parcel in inputParcels.iterrows():
        inputPriorityScores.loc[parcel[1][polygonIdColumn]] = priorityCalculator.extractPriorityScoreForPolygonAsArray(parcel[1]['geometry'], False)        

    return inputPriorityScores    