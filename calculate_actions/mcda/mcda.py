from common.qeia import QEIAMatrix
import pandas as pd
import re

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

def calculateMCDAForPriorityScoresWithEligibility(priorityScores: pd.DataFrame, qeia: QEIAMatrix, eligibility: pd.DataFrame, activeServicesMatrixPath: str = "", activeServicesScorePath: str = "") -> pd.DataFrame:
    """Calcualate the MCDA outputs for a supplied set of priority scores, QEIA matrix and eligibility table

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        qeia (QEIAMatrix): The QEIA matrix to use for this MCDA calculation
        eligibility (pd.DataFrame): The base eligibility table for each input polygon ID

    Returns:
        pd.DataFrame: A finalised MCDA table with total/rank for each input polygon ID
    """
    
    template = eligibilityTableToMCDAEligibilityTemplate(eligibility[eligibility.index.isin(priorityScores.index)])
    qeiaMultiplier = eligibilityTemplateToQEIAMultiplier(template, qeia)
    
    ecosystemServices = sorted(set([re.match(r"Priority_(\w+)_\w+",x).group(1) for x in priorityScores.columns]))
    
    ecosystemServiceApplicable = pd.DataFrame({'id': priorityScores.index})
    ecosystemServiceApplicable.set_index('id', inplace=True)

    for service in ecosystemServices:
        serviceColumn = priorityScores.columns[priorityScores.columns.str.startswith(f'Priority_{service}_')]
        if serviceColumn.empty:
            raise ValueError(f'No priority scores columns found for service {service} in {priorityScores.columns.tolist()}')
        ecosystemServiceApplicable[service] = priorityScores[serviceColumn].notna().any(axis = 1)

    ecosystemServiceApplicable['totalServices'] = ecosystemServiceApplicable.sum(axis=1)

    if activeServicesMatrixPath.strip():
        print(ecosystemServiceApplicable)
        ecosystemServiceApplicable.to_csv(activeServicesMatrixPath, index=True) 
    
    mcda = priorityScores.merge(template, on='id')
    mcda = mcda.merge(ecosystemServiceApplicable['totalServices'], on='id', how='left')
    mcda.set_index(['id', 'option'], inplace=True)

    data_columns = mcda.columns.difference(['id', 'option', 'totalServices'])
    mcda = mcda.apply(lambda row: (1 / row['totalServices']) * row[data_columns], axis=1)
    mcda['serviceSum'] = mcda[data_columns].sum(axis=1)

    mcda = mcda.apply(lambda row: row[data_columns] / row['serviceSum'], axis=1)

    print(activeServicesScorePath)
    if activeServicesScorePath.strip():
        activeServicesScore = mcda.reset_index().drop(columns=['option']).drop_duplicates().set_index('id')
        activeServicesScore['total'] = activeServicesScore[data_columns].sum(axis=1)
        print(activeServicesScore)
        activeServicesScore.to_csv(activeServicesScorePath, index=True)

    mcda = mcda[data_columns].mul(qeiaMultiplier)    

    mcda['total'] = mcda[data_columns].sum(axis=1)
    mcda['rank'] = mcda.groupby(level=0)['total'].rank(method='first', ascending=False)

    return mcda.sort_values(['id', 'rank'])
