from common.qeia import Filtered as FilteredQeia
import numpy as np
import pandas as pd

def calculateMultiCriteriaDecisionAnalysisForParcel(weightedScores: dict[str, np.floating], filteredQeia: FilteredQeia) -> pd.DataFrame:
    mcda = {}

    for option in filteredQeia.qeia:
        mcda[option] = {}
        total: np.float64 = 0

        for priority in filteredQeia.qeia[option]:
            mcdaValue = weightedScores[priority] * filteredQeia.qeia[option][priority]
            total = total + (0 if np.isnan(mcdaValue) else mcdaValue)
            mcda[option][priority] = mcdaValue
        mcda[option]['total'] = total
    
    #sortedMcda = {val[0]: val[1] for val in sorted(mcda.items(), key = lambda x: (-x[1]['total'], x[0]))}
    df =  multiCriteriaDecisionAnalysisToRows(mcda)
    df['rank'] = df['total'].rank(method='first', ascending=False)
    return df.sort_values('rank')

def multiCriteriaDecisionAnalysisToRows(mcda: dict[str, dict[str, np.floating]]) -> pd.DataFrame:
    row = {}
    
    for option in mcda:
        row[option] = mcda[option]

    return pd.DataFrame.from_dict(row).transpose()
