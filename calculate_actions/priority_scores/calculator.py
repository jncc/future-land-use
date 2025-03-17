from common.layers import PriorityLayer
from common.timing import startTimers, endTimers
from shapely import Polygon
import logging
import numpy as np

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