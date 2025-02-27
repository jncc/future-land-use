from common.layers import PriorityLayer
import numpy as np

class Weighting:
    DECIMAL_PLACES = 2
    priorityLayers: dict[str, PriorityLayer]

    def __init__(self, priorityLayers: dict[str, PriorityLayer]):
        self.priorityLayers = priorityLayers
    
    def calculateWeightings(self, scores: dict[str, np.float64]) -> dict[str, np.floating]:
        weightedScores: dict[str, np.floating] = {}

        for score in scores:
            weightedScores[score] = self.priorityLayers[score].calculateWeightedScore(scores[score])
        
        return weightedScores

