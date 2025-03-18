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

    def calculatePriorityScoreForPolygon(self, polygon: Polygon, timing: bool = True) -> dict[str, np.floating]:
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

            df[layer] = self.priorityLayers[layer].calculateScore(polygon)

            if timing:
                (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

                logging.info(f'--- Processed priority layer: {self.priorityLayers[layer].name}')
                logging.info(f'--- Wall Time: {wallTime} milliseconds')
                logging.info(f'--- Process Time: {processTime} milliseconds')

        return df

    def calculatePriorityScoreForPolygonAsArray(self, polygon: Polygon, timing: bool = True) -> list[np.floating]:
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

            df.append(self.priorityLayers[layer].calculateScore(polygon))

            if timing:
                (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

                logging.info(f'--- Processed priority layer: {self.priorityLayers[layer].name}')
                logging.info(f'--- Wall Time: {wallTime} milliseconds')
                logging.info(f'--- Process Time: {processTime} milliseconds')

        return df
    
def calculatePriorityScoresForInputPolygon(polygonId: str, polygon: Polygon, prioirityLayers: dict[str, PriorityLayer]) -> pd.DataFrame:
    """Calculate the priority scores for the input polygon, using the provided priority layers

    Args:
        polygonId (str): A unique identifier for the input polygon
        polygon (Polygon): The input polygon to calculate the priority scores for
        prioirityLayers (dict[str, PriorityLayer]): A dictionary containing the priority layers to use in the calculation

    Returns:
        pd.DataFrame: A DataFrame containing the priority scores for the input polygon
    """
    priorityCalculator = Calculator(prioirityLayers)
    inputPriorityScores = pd.DataFrame(columns=prioirityLayers.keys())
    inputPriorityScores.index.name = 'id'

    inputPriorityScores.loc[polygonId] = priorityCalculator.calculatePriorityScoreForPolygonAsArray(polygon, False)

    return inputPriorityScores

def calculatePriorityScoresForInputPolygons(polygonSource: Path, prioirityLayers: dict[str, PriorityLayer], polygonIdColumn: str) -> pd.DataFrame:
    """Calculate the priority scores for the input polygon, using the provided priority layers

    Args:
        polygonSource (Path): A path to a WKT file containing the input polygon
        prioirityLayers (dict[str, PriorityLayer]): A dictionary containing the priority layers to use in the calculation

    Returns:
        pd.DataFrame: A DataFrame containing the priority scores for the input polygon
    """
    inputParcels = gpd.read_file(polygonSource)
    priorityCalculator = Calculator(prioirityLayers)
    inputPriorityScores = pd.DataFrame(columns=prioirityLayers.keys())
    inputPriorityScores.index.name = 'id'

    for parcel in inputParcels.iterrows():
        inputPriorityScores.loc[parcel[1][polygonIdColumn]] = priorityCalculator.calculatePriorityScoreForPolygonAsArray(parcel[1]['geometry'], False)        

    return inputPriorityScores    