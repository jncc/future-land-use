from common.layers import PriorityLayer
import numpy as np

class Weighting:
    """Helper class to calculate weighted scores given an input
    """
    priorityLayers: dict[str, PriorityLayer]

    def __init__(self, priorityLayers: dict[str, PriorityLayer]):
        """Sets the prioirty layers dict object to loop through and calcuate weighted scores

        Args:
            priorityLayers (dict[str, PriorityLayer]): A dict containig name / priorityLayer pairs
            to extract the weightings from
        """
        self.priorityLayers = priorityLayers
    
    def calculateWeightingScores(self, scores: dict[str, np.float64]) -> dict[str, np.floating]:
        """Calculate the weighted scores for a given set of name / scores

        Args:
            scores (dict[str, np.float64]): Original scores for each prioirty layer

        Returns:
            dict[str, np.floating]: Weighted scores for each priority layer
        """
        weightedScores: dict[str, np.floating] = {}

        for score in scores:
            weightedScores[score] = self.priorityLayers[score].calculateWeightedScore(scores[score])
        
        return weightedScores

