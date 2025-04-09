import numpy as np
import pandas as pd

def calculateWeightedPriorityScores(priorityScores: pd.DataFrame, weightings: dict[str, np.floating]) -> pd.DataFrame:
    """Taking in a Priority Scores dataframe, multiply the columns of that dataframe with the matching weighting
    value from the weightings config object

    Args:
        priorityScores (pd.DataFrame): Input priority scores dataframe
        weightings (dict[str, np.floating]): A dictionaty of layer name / modifier pairs

    Returns:
        pd.DataFrame: A priority score dataframe with the weightings applied
    """
    for layer in priorityScores.columns:
        weight = np.float64(weightings[layer])
        priorityScores[layer] = priorityScores[layer].apply(lambda x: x * weight)

    return priorityScores
