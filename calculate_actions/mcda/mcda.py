from common.qeia import QEIAMatrix
import pandas as pd

def templateToQEIAMultiplier(template: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
    """Creates a multiplier dataframe from an eligibility template and a QEIA matrix, to allow us to
    multiply the eligibility template by the QEIA matrix

    Args:
        eligibilityTemplate (pd.DataFrame): A template dataframe with a row for each parcel ID/ eligible 
        option pair (generated from the eligibilityTableToMCDAEligibilityTemplate function)
        qeia (QEIAMatrix): The QEIA matrix to use for this MCDA calculation

    Returns:
        pd.DataFrame: A utility dataframe containing the QEIA multipliers for each parcel ID/option pair
    """
    qeiaMatrix = qeia.createDataFrame().transpose()
    qeiaMatrix.index.name = 'option'
    qeiaMatrix.drop(columns=template.columns.difference(qeiaMatrix.columns), inplace=True)

    # 0 out the template
    template = template.copy()
    for col in template.columns:
        template[col].values[:] = 0

    for column in qeiaMatrix.columns:
        for option in qeiaMatrix.index:
            if option in template.index.get_level_values('option'):
                template.loc[pd.IndexSlice[:, option], column] = qeiaMatrix.loc[option, column]

    return template

def calculateMCDAForPriorityScoresWithEligibility(priorityScores: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
    """Calcualate the MCDA outputs for a supplied set of priority scores, QEIA matrix and eligibility table

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        qeia (QEIAMatrix): The QEIA matrix to use for this MCDA calculation

    Returns:
        pd.DataFrame: A finalised MCDA table with total/rank for each input polygon ID
    """
    
    qeiaMultiplier = templateToQEIAMultiplier(priorityScores, qeia)
    mcda = priorityScores.mul(qeiaMultiplier)
    mcda['total'] = mcda.sum(axis=1)
    mcda['rank'] = mcda.groupby(level=0)['total'].rank(method='first', ascending=False)

    return mcda.sort_values(['id', 'rank'])
