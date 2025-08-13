import pandas as pd
import re

def calculateActiveServices(priorityScores: pd.DataFrame, outputPath: str, writeOutput: bool = False) -> pd.DataFrame:
    """Calculate the active services from the priority scores DataFrame, and optionally write to a CSV file

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        outputPath (str): Path to save the active services matrix CSV file
        writeOutput (bool, optional): Whether to write the output to a file. Defaults to False.
    
    Raises:
        ValueError: If no priority scores columns are found for a service in the priorityScores DataFrame
        ValueError: If the priorityScores DataFrame is empty or does not contain the expected columns

    Returns:
        pd.DataFrame: A DataFrame containing the active services for each input polygon ID
    """
    ecosystemServices = sorted(set([re.match(r"Priority_(\w+)_\w+",x).group(1) for x in priorityScores.columns]))
    
    ecosystemServiceApplicable = pd.DataFrame({'id': priorityScores.index})
    ecosystemServiceApplicable.set_index('id', inplace=True)

    for service in ecosystemServices:
        serviceColumn = priorityScores.columns[priorityScores.columns.str.startswith(f'Priority_{service}_')]
        if serviceColumn.empty:
            raise ValueError(f'No priority scores columns found for service {service} in {priorityScores.columns.tolist()}')
        ecosystemServiceApplicable[service] = priorityScores[serviceColumn].fillna(0).any(axis = 1)

    ecosystemServiceApplicable['totalServices'] = ecosystemServiceApplicable.sum(axis=1)

    if writeOutput:
        print(ecosystemServiceApplicable)
        ecosystemServiceApplicable.to_csv(outputPath, index=True) 

    return ecosystemServiceApplicable

def groupColumnAggregation(priorityScores: pd.DataFrame, group: str, eligibleOptions: dict[str, list[str]], operation: str = 'MAX') -> pd.DataFrame:
    """Aggregate the priority scores for a given group, applying eligibility options and option eligibility

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        group (str): The group to aggregate the priority scores for
        eligibleOptions (dict[str, list[str]]): A list of eligible options for each option set

    Returns:
        pd.DataFrame: A DataFrame containing the aggregated priority scores for the specified group
    """

    # Get group columns based on the group name
    groupColumns = [col for col in priorityScores.columns if re.match(fr'{group}(_(\w+)){{1}}', col)]

    # For each option, set the priority scores to None for columns not in the eligible options
    for option in eligibleOptions.keys():
        # Get all columns that match the option
        optionColumns = [f'{group}_{opt}' for opt in eligibleOptions[option]]
        # Set the priority scores to None for columns that are not in the optionColumns group
        priorityScores.loc[pd.IndexSlice[:,option], priorityScores[groupColumns].columns.difference(optionColumns)] = None

    match operation:
        case 'MAX':
            priorityScores[f'{group}'] = priorityScores[groupColumns].max(axis=1, skipna=True)
        case 'MIN':
            priorityScores[f'{group}'] = priorityScores[groupColumns].min(axis=1, skipna=True)
        case 'AVG':
            priorityScores[f'{group}'] = priorityScores[groupColumns].mean(axis=1, skipna=True)
        case _:
            raise ValueError(f'Unsupported operation {operation} for group aggregation')
        
    return priorityScores.drop(columns=groupColumns, errors='ignore')

def calculateInitialPriorityScoreWeighting(priorityScores: pd.DataFrame) -> pd.DataFrame:
    """Calculate the initial priority score weighting based on the QEIA matrix and eligibility table

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID

    Returns:
        pd.DataFrame: A DataFrame containing the initial priority score weighting
    """
    data_columns = priorityScores.columns.difference(['id', 'option', 'totalServices'])
    priorityScores = priorityScores.apply(lambda row: (1 / row['totalServices']) * row[data_columns], axis=1)
    priorityScores['serviceSum'] = priorityScores[data_columns].sum(axis=1)
    print(priorityScores)

    return priorityScores.apply(lambda row: row[data_columns] / row['serviceSum'], axis=1).drop(columns=['serviceSum','totalServices'], errors='ignore')

def calculatePriorityScoreWeighting(priortyScores: pd.DataFrame, weigthings: dict[str, float]) -> pd.DataFrame:
    """Calculate the priority score weighting based on the provided weights

    Args:
        priortyScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        weigthings (dict[str, float]): A dictionary containing the weights for each priority layer

    Returns:
        pd.DataFrame: A DataFrame containing the weighted priority scores
    """
    for layer, weight in weigthings.items():
        if layer in priortyScores.columns:
            priortyScores[layer] *= weight
        else:
            raise ValueError(f'Layer {layer} not found in priority scores columns')

    # Normalize the scores to ensure they sum to 1
    priortyScores['total'] = priortyScores.sum(axis=1)
    priortyScores = priortyScores.apply(lambda row: row / row['total'], axis=1)
    priortyScores.drop(columns=['total'], inplace=True)

    return priortyScores