from common.PriorityLayer import PriorityLayer
import numpy as np

class Weighting:
    DECIMAL_PLACES = 2
    priorityLayers: list[PriorityLayer]

    def __init__(self, priorityLayers: list[PriorityLayer]):
        self.priorityLayers = priorityLayers
    
    def getWeightingForName(self, name:str) -> float:
        return np.round(np.float64(next(iter([layer for layer in self.priorityLayers if layer.name is name])).weighting), 2)
    
    def calculateSingleWeighting(self, name, score):
        return (name, score * self.getWeightingForName(name))

    def calculateWeightings(self, scores: list[(str, np.float64)]):
        weightedScores = []

        for score in scores:
            weightedScores.append(self.calculateSingleWeighting(score[0], score[1]))
        
        return weightedScores

