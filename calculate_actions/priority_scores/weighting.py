from common.layers import PriorityLayer
import numpy as np
import pandas as pd

def createWeightingTable(priorityScores: pd.DataFrame, weightings: dict[str, np.floating]) -> pd.DataFrame:
    for layer in weightings:
        priorityScores = priorityScores.assign(layer = weightings[layer])

    return priorityScores

def calculateWeightedPriorityScores(priorityScores: pd.DataFrame, weightings: dict[str, np.floating]) -> pd.DataFrame:
    weightingTable = createWeightingTable(priorityScores, weightings)

    return priorityScores.multiply(weightingTable)
