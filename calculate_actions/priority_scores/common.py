import pandas as pd

def mergeEligibilityOptions(priorityScores: pd.DataFrame, eligibility: pd.DataFrame) -> pd.DataFrame:
    """Merge the eligibility options with the priority scores DataFrame

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        eligibility (pd.DataFrame): Dataframe containing the eligibility options for each input polygon ID

    Returns:
        pd.DataFrame: A DataFrame containing the merged priority scores and eligibility options
    """
    eligbilitySeries = eligibility.agg(lambda x: [col for i, col in enumerate(eligibility.columns) if x.iloc[i]], axis=1)

    eligiblityTemplate = pd.DataFrame(eligbilitySeries.explode(), columns=['option']).dropna(subset=['option'])
    eligiblityTemplate.index.name = 'id'

    merged = priorityScores.merge(eligiblityTemplate, on='id', how='left').reset_index()
    merged.set_index(['id', 'option'], inplace=True)

    return merged