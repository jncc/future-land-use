from common.layers import EligibilityLayer
from common.timing import startTimers, endTimers
from shapely import Polygon

import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

class Calculator:
    """Calculator object to determine option eligibility for a set of polygons
    """
    eligibilityLayer: dict[str, EligibilityLayer]

    def __init__(self, eligibilityLayer: dict[str, EligibilityLayer]):
        """Set the EligibiliyLayer dict object for use in determining option eligibility

        Args:
            eligibilityLayer (dict[str, EligibilityLayer]): A dict of name / configured EligibilityLayer
            values to determine option eligibility for polygons
        """
        self.eligibilityLayer = eligibilityLayer

    def determineEligibilityForPolygon(self, polygon: Polygon) -> list[str]:
        """Determines the eligible options for a given Polygon iterating through all configured
        EligibilityLayers, each eligiblity layer may potentially contian mutliple options but currently
        it is only one option per layer

        Args:
            polygon (Polygon): Polygon to interesct with eligibilty layers

        Returns:
            list[str]: A list of eligible options for the input polygon
        """
        df: set[str] = set([])
        
        for layer in self.eligibilityLayer:
            (startWallTime, startProcessTime) = startTimers()

            (eligible, options) = self.eligibilityLayer[layer].determineEligibility(polygon)
            if eligible:
                for option in options:
                    df.add(option)

            (wallTime, processTime) = endTimers(startWallTime, startProcessTime)

            logging.info(f'--- Processed eligibility layer: {self.eligibilityLayer[layer].name}')
            logging.info(f'--- Wall Time: {wallTime} milliseconds')
            logging.info(f'--- Process Time: {processTime} milliseconds')

        return list(df)

    def createOutputTableRow(self, id: str, options: list[str], eligibleOptions: list[str]) -> pd.DataFrame:
        """Helper function to output data in a human viewable format table

        Args:
            id (str): ID for the polygon
            options (list[str]): A list of all potential options
            eligibleOptions (list[str]): A list of all eligible options

        Returns:
            pd.DataFrame: A table of eligible options for a given polygon
        """
        row = {'id': [id]}
        
        for option in options:
            row[option] = [option in eligibleOptions]

        return pd.DataFrame.from_dict(row)