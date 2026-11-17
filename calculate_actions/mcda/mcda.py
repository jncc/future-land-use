from common.qeia import QEIAMatrix
import pandas as pd

def templateToQEIAMultiplier(template: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
    """Creates a multiplier dataframe from an eligibility template and a QEIA matrix, to allow us to
    multiply the eligibility template by the QEIA matrix

    Args:
        template (pd.DataFrame): A template dataframe with a row for each parcel ID/ eligible
        option pair (generated from the eligibilityTableToMCDAEligibilityTemplate function)
        qeia (QEIAMatrix): The QEIA matrix to use for this MCDA calculation

    Returns:
        pd.DataFrame: A utility dataframe containing the QEIA multipliers for each parcel ID/option pair
    """
    qeiaMatrix = qeia.createDataFrame().transpose()
    qeiaMatrix.index.name = 'option'
    qeiaMatrix.drop(columns=qeiaMatrix.columns.difference(template.columns), inplace=True)

    # 0 out the template
    output = template.copy(deep=True)    

    # Use pandas assignment instead of NumPy view mutation to avoid read-only buffers.
    output.loc[:, output.columns] = 0

    for column in qeiaMatrix.columns:
        for option in qeiaMatrix.index:
            if option in output.index.get_level_values('option'):
                output.loc[pd.IndexSlice[:, option], column] = qeiaMatrix.loc[option, column]

    return output

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
    mcda.loc[:, 'total'] = mcda.sum(axis=1)
    mcda.loc[:, 'rank'] = mcda.groupby(level=0)['total'].rank(method='first', ascending=False)

    return mcda.sort_values(['id', 'rank'])
