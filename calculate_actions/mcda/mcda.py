from common.qeia import QEIAMatrix
import pandas as pd

def eligibilityTableToMCDAEligibilityTemplate(eligibilityTable: pd.DataFrame) -> pd.DataFrame:
    """Creates a template dataframe for MCDA calculations from an eligibility table, to allow us
    to do some table multiplication more easily

    Args:
        eligibilityTable (pd.DataFrame): A dataframe containing the general option eligibility for 
        each input polygon, each column containing True/False values for the eligibility of each
        option

    Returns:
        pd.DataFrame: An exploded dataframe with a line for each parcel ID/option pair ready to be
        worked with
    """
    eligbilitySeries = eligibilityTable.agg(lambda x: [col for i, col in enumerate(eligibilityTable.columns) if x.iloc[i]], axis=1)

    eligiblityTemplate = pd.DataFrame(eligbilitySeries.explode(), columns=['option']).dropna(subset=['option'])
    eligiblityTemplate.index.name = 'id'
    return eligiblityTemplate.reset_index()

def eligibilityTemplateToQEIAMultiplier(eligibilityTemplate: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
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

    return eligibilityTemplate.merge(qeiaMatrix, on='option').set_index(['id', 'option'])

def calculateMCDAForPriorityScoresWithEligibility(priorityScores: pd.DataFrame, qeia: QEIAMatrix, eligibility: pd.DataFrame) -> pd.DataFrame:
    """Calcualate the MCDA outputs for a supplied set of priority scores, QEIA matrix and eligibility table

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        qeia (QEIAMatrix): The QEIA matrix to use for this MCDA calculation
        eligibility (pd.DataFrame): The base eligibility table for each input polygon ID

    Returns:
        pd.DataFrame: A finalised MCDA table with total/rank for each input polygon ID
    """
    template = eligibilityTableToMCDAEligibilityTemplate(eligibility)
    qeiaMultiplier = eligibilityTemplateToQEIAMultiplier(template, qeia)
    mcda = priorityScores.merge(template, on='id')
    mcda.set_index(['id', 'option'], inplace=True)   
    mcda = mcda.mul(qeiaMultiplier)
    mcda['total'] = mcda.sum(axis=1)
    mcda['rank'] = mcda.groupby(level=0)['total'].rank(method='first', ascending=False)

    return mcda.sort_values(['id', 'rank'])
