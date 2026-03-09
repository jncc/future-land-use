import pandas as pd
import logging
import re

def calculateActiveServices(priorityScores: pd.DataFrame) -> pd.DataFrame:
    """Calculate the active services from the priority scores DataFrame, and optionally write to a CSV file

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
    
    Raises:
        ValueError: If no priority scores columns are found for a service in the priorityScores DataFrame
        ValueError: If the priorityScores DataFrame is empty or does not contain the expected columns

    Returns:
        pd.DataFrame: A DataFrame containing the active services for each input polygon ID
    """
    ecosystemServices = sorted(set([re.match(r"Priority_([a-zA-Z0-9]+)_\w+",x).group(1) for x in priorityScores.columns]))
    
    ecosystemServiceApplicable = pd.DataFrame({'id': priorityScores.index})
    ecosystemServiceApplicable.set_index('id', inplace=True)

    for service in ecosystemServices:
        serviceColumn = priorityScores.columns[priorityScores.columns.str.startswith(f'Priority_{service}_')]
        if serviceColumn.empty:
            raise ValueError(f'No priority scores columns found for service {service} in {priorityScores.columns.tolist()}')
        ecosystemServiceApplicable[service] = priorityScores[serviceColumn].fillna(0).any(axis = 1)

    ecosystemServiceApplicable['totalServices'] = ecosystemServiceApplicable.sum(axis=1)

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
        
        # Check if any values for the option are eligible
        if f'Eligibility_{option}' in priorityScores.index.get_level_values('option'):
            # Set the priority scores to None for columns that are not in the optionColumns group
            priorityScores.loc[pd.IndexSlice[:,f'Eligibility_{option}'], priorityScores[groupColumns].columns.difference(optionColumns)] = None
        else:
            logging.info(f'Option {option} is never eligible for group {group}, skipping')

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
    priorityScores['serviceSum'] = priorityScores[data_columns].sum(axis=1)
    # Find the maximum possible service sum per parcel and use that for normalisation per parcel
    priorityScores['serviceSum'] = priorityScores.groupby(['id'])['serviceSum'].transform("max")
    priorityScores = priorityScores.apply(lambda row: row[data_columns] / row['serviceSum'], axis=1).drop(columns=['serviceSum','totalServices'], errors='ignore')

    """Below is code for the alternate function with normalisation per service and multiplication
    by 1/n(ES) - not using this for now

    # Normalise so that scores sum to 1 per ecosystem service
    ecosystemServices = list(set([i.split("_")[1] for i in data_columns]))

    for service in ecosystemServices:
        serviceColumns = list(filter(lambda k: service in k, data_columns))

        priorityScores['serviceSum'] = priorityScores[serviceColumns].sum(axis=1)
        priorityScores['serviceSum'] = priorityScores.groupby(['id'])['serviceSum'].transform("max")

        serviceColumns.append("serviceSum")
        priorityScores[serviceColumns] = priorityScores[serviceColumns].apply(lambda row: row / row['serviceSum'], axis=1)
        priorityScores.drop(columns=['serviceSum'], inplace=True)
    
    # Multiply by 1/n(ES) so that scores sum to 1 per parcel
    # (In the future this will be replaced with the service weighting calculations)
    priorityScores = priorityScores.apply(lambda row: (1 / row['totalServices']) * row[data_columns], axis=1)
    """

    # Trialling alternative method to incorporate 1/n(ES): multiply by 1/n(ES), then divide
    # this by number of indicators within each service

    ecosystemServices = list(set([i.split("_")[1] for i in data_columns]))

    for service in ecosystemServices:
        # Find service columns, i.e. indices for that service
        serviceColumns = list(filter(lambda k: service in k, data_columns))
        # Weighting = (1 / total number of ecosystem services) / number of indicators in that service
        weighting = ((1/len(ecosystemServices)) / len(serviceColumns))
        # Multiply weighting with priority scores
        priorityScores[serviceColumns] = priorityScores[serviceColumns].apply(lambda row: weighting * row, axis=1)

    return priorityScores

def calculatePriorityScoreWeighting(priorityScores: pd.DataFrame, weightings: dict[str, float]) -> pd.DataFrame:
    """Calculate the priority score weighting based on the provided weights

    Args:
        priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
        weightings (dict[str, float]): A dictionary containing the weights for each priority layer

    Returns:
        pd.DataFrame: A DataFrame containing the weighted priority scores
    """
    # This code will need to be updated with the new weighting approach 
    # (but doesn't make a difference now as we are not weighting services)
    for layer, weight in weightings.items():
        if layer in priorityScores.columns:
            priorityScores[layer] *= weight
        else:
            raise ValueError(f'Layer {layer} not found in priority scores columns')

    # Normalize the scores to ensure they sum to 1
    priorityScores['total'] = priorityScores.sum(axis=1)
    priorityScores = priorityScores.apply(lambda row: row / row['total'], axis=1)
    priorityScores.drop(columns=['total'], inplace=True)

    return priorityScores