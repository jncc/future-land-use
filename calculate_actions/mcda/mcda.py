from common.qeia import QEIAMatrix, QEIAOption
from common.layers import PriorityLayer
import numpy as np
import pandas as pd

def calculateMultiCriteriaDecisionAnalysisForParcel(weightedScores: dict[str, np.floating], filteredQeia: QEIAMatrix) -> pd.DataFrame:
    mcda = {}

    for option in filteredQeia.options:
        mcda[option] = {}
        total: np.float64 = 0

        for priority in filteredQeia.options[option].getPriorityModifiers():
            mcdaValue = weightedScores[priority] * filteredQeia.options[option].getPriorityModifier(priority)
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

def eligibilityTableToMCDAEligibilityTemplate(eligibilityTable: pd.DataFrame) -> pd.DataFrame:
    eligbilitySeries = eligibilityTable.agg(lambda x: [col for i, col in enumerate(eligibilityTable.columns) if x.iloc[i]], axis=1)

    return pd.DataFrame(eligbilitySeries.explode(), columns=['option']).reset_index().dropna(subset=['option'])

def eligibilityTemplateToQEIAMultiplier(eligibilityTemplate: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
    qeiaMatrix = qeia.createDataFrame().transpose()
    qeiaMatrix.index.name = 'option'

    return eligibilityTemplate.merge(qeiaMatrix, on='option').set_index(['id', 'option'])

def calculateMCDAForPriorityScoresWithEligibility(priorityScores: pd.DataFrame, qeia: QEIAMatrix, eligibility: pd.DataFrame) -> pd.DataFrame:
    template = eligibilityTableToMCDAEligibilityTemplate(eligibility)
    qeiaMultiplier = eligibilityTemplateToQEIAMultiplier(template, qeia)
    mcda = priorityScores.merge(template, on='id').set_index(['id', 'option'])
    mcda = mcda.multiply(qeiaMultiplier)
    mcda['total'] = mcda.sum(axis=1)
    mcda['rank'] = mcda.groupby(level=0)['total'].rank(method='first', ascending=False)

    return mcda.sort_values(['id', 'rank'])
