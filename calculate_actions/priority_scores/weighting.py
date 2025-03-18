from common.layers import PriorityLayer
import numpy as np
import pandas as pd

def createWeightingTable(priorityScores: pd.DataFrame, weightings: dict[str, np.floating]) -> pd.DataFrame:
    weightingTable = priorityScores.copy()
    for layer in weightings:
        weightingTable[layer] = weightings[layer]

    return weightingTable

def calculateWeightedPriorityScores(priorityScores: pd.DataFrame, weightings: dict[str, np.floating]) -> pd.DataFrame:
    weightingTable = createWeightingTable(priorityScores, weightings)

    return priorityScores.multiply(weightingTable)
