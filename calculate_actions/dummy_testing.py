import pandas as pd
import numpy as np
import json
from common.qeia import QEIAMatrix

# PART 1: ORIGINAL WEIGHTINGS TESTING ################################################################################################################################

# dummy_path = "O:/EAT/Ecosystems Analysis/ELMs/Spatial Prioritisation v2.0/Data/MCDA Workflow Data/MCDA Change Tests/dummy_data/Dummy_Data_For_Weightings.csv"
# dummy_ps = pd.read_csv(dummy_path)
# print("Dummy dataframe read in:")
# print(dummy_ps)

# # Initial priority score weighting function code - creates a list of data columns
# data_columns = dummy_ps.columns.difference(['Parcel', 'Option', 'Active Service Sum'])
# print("Data columns:")
# print(data_columns)

# # 1/n(ES) code - comment out as not relevant to option level fix
# # priorityScores = dummy_ps.apply(lambda row: (1 / row['Active Service Sum']) * row[data_columns], axis=1)
# # print("priorityScores after lambda:")
# # print(priorityScores)
# priorityScores = dummy_ps
# priorityScores['serviceSum'] = priorityScores[data_columns].sum(axis=1)
# print("priorityScores:")
# print(priorityScores)
# priorityScores = priorityScores.apply(lambda row: row[data_columns] / row['serviceSum'], axis=1)
# print("priorityScores return:")
# print(priorityScores) 

# # From calculate priority score weighting function:
# # Normalise the scores to ensure they sum to 1
# print("Normalise code:")
# priorityScores['total'] = priorityScores.sum(axis=1)
# print(priorityScores)

# priorityScores = priorityScores.apply(lambda row: row / row['total'], axis=1)
# print("apply lambda")
# print(priorityScores)

# # ALTERNATIVE 1: Instead of dividing by service sum per row, divide by the maximum
# # service sum per parcel to get the same weighted priority score for layers present
# # in all options per parcel
# # (This only affects the outputs in cases where there has been a lookup with SNH indicators
# # as they are the only ones that will have nulls for some options and priority scores for others)
# alt_pS = dummy_ps
# alt_pS['serviceSum'] = alt_pS[data_columns].sum(axis=1)
# alt_pS['max_serviceSum'] = alt_pS.groupby(['Parcel'])['serviceSum'].transform("max")
# print("Max service sum:")
# print(alt_pS)

# alt_pS_out = alt_pS.apply(lambda row: row[data_columns] / row['max_serviceSum'], axis=1)
# print("Divide by max service sum:")
# print(alt_pS_out)

# # ALTERNATIVE 2: Group the weightings by services (so they sum to 1 within a service
# # area)
# print("ALTERNATIVE 2")
# alt_pS_2 = alt_pS
# # Get unique services present
# services = list(set([i.split("_")[1] for i in data_columns]))
# print(services)
# # unique_services = list(set(services))
# # print(unique_services)

# for i in services:
#     print("Service: ", i)
#     service_columns = list(filter(lambda k: i in k, data_columns))
#     print("Service columns: ", service_columns)

#     alt_pS_2['service_sum'] = alt_pS_2[service_columns].sum(axis=1)
#     alt_pS_2['service_sum'] = alt_pS_2.groupby(['Parcel'])['service_sum'].transform("max")

#     service_columns.append("service_sum")
#     alt_pS_2[service_columns] = alt_pS_2[service_columns].apply(lambda row: row / row['service_sum'], axis = 1)
#     alt_pS_2.drop(columns=['service_sum'], inplace=True)

#     print(alt_pS_2)

# alt_pS_2.drop(columns=['serviceSum', 'max_serviceSum'], inplace=True)
# print("Weighted per service:")
# print(alt_pS_2)

# # This wouldn't generally be recommended to be used as the final priority score
# # in an MCDA without being made to sum to 1, but in order to test whether the last
# # 1/n(ES) step is having an effect this will be done

# # ALTERNATIVE 3: Use 1/n(ES) to have all present priority scores per parcel add to 1
# # and make the MCDA follow the simple additive weighting (SAW) approach

# # The active service sum calculation will need to be ammended to make sure it is
# # summing services, not indicators

# print("ALTERNATIVE 3")
# alt_pS_3 = alt_pS_2
# alt_pS_3 = alt_pS_3.apply(lambda row: (1 / row['Active Service Sum']) * row[data_columns], axis=1)
# print("1/n(ES) applied:")
# print(alt_pS_3)

# # ALTERNATIVE 4: Using Rory's suggestion of multiplying by (1/n(ES))/n(EiS) per service
# # to adjust scores for services with more indicators

# print("ALTERNATIVE 4")
# # zPS/sum(zPS) with parcel weighting fix

# alt_pS_4 = alt_pS
# print(alt_pS_4)
# # Add another column to test df with an inactive service for one of the parcels
# alt_pS_4['Priority_Biod_TestInd'] = [1.0, 1.0, 1.0, float("nan"), float("nan"), float("nan")]
# print("Initial data:")
# print(alt_pS_4)

# alt_pS_4['serviceSum'] = alt_pS_4[data_columns].sum(axis=1)
# alt_pS_4['max_serviceSum'] = alt_pS_4.groupby(['Parcel'])['serviceSum'].transform("max")
# print(alt_pS_4)
# data_columns = alt_pS_4.columns.difference(['Parcel', 'Option', 'Active Service Sum'])
# print("Data columns: ", data_columns)
# alt_pS_4[data_columns] = alt_pS_4[data_columns].apply(lambda row: row[data_columns] / row['max_serviceSum'], axis=1)
# alt_pS_4.drop(columns=['Active Service Sum', 'serviceSum', 'max_serviceSum'], inplace=True)
# print("Parcel weighting:")
# print(alt_pS_4)
# print("n(ES) = ", len(services))

# alt_pS_4.groupby(['Parcel'])
# """ print("Grouped:")
# print(alt_pS_4) """

# for i in services:
#     print("Service: ", i)
#     service_columns = list(filter(lambda k: i in k, data_columns))
#     print("Service columns: ", service_columns)
#     print("Number of indicators: ", len(service_columns))

#     print("( 1/", len(services), " / ", len(service_columns), ")")
#     multiplier = ((1/len(services)) / len(service_columns))
#     print(multiplier)

#     alt_pS_4[service_columns] = alt_pS_4[service_columns].apply(lambda row: multiplier * row)

# print(alt_pS_4)


## PART 2: TESTING QEIA DOWNSCALING ######################################################################################################################################################
print("TESTING: QEIA DOWNSCALING =================================================================================")
# Read in new dummy priority scores and dummy QEIA

dummy_path = "O:/EAT/Ecosystems Analysis/ELMs/Spatial Prioritisation v2.0/Data/MCDA Workflow Data/MCDA Change Tests/dummy_data/"
dummy_ps = pd.read_csv(dummy_path + "Dummy_Data_2.csv")

# Convert all int column values to float
cols = list(dummy_ps.columns)
cols.remove('Option')
for col in cols:
    dummy_ps[col] = dummy_ps[col].astype(float)

print("Dummy priority scores:")
print(dummy_ps)
#dummy_ps.to_clipboard()

# Apply new priority score weighting approach - normalising by max service sum:
data_columns = dummy_ps.columns.difference(['Parcel', 'Option'])
print(data_columns)
dummy_ps['serviceSum'] = dummy_ps[data_columns].sum(axis=1)
dummy_ps['max_serviceSum'] = dummy_ps.groupby(['Parcel'])['serviceSum'].transform("max")
weighting_columns = dummy_ps.columns.difference(['Parcel', 'Option', 'serviceSum'])
dummy_ps[weighting_columns] = dummy_ps[weighting_columns].apply(lambda row: row / row['max_serviceSum'], axis=1)
dummy_ps.drop(columns=['serviceSum', 'max_serviceSum'], inplace=True)
print("Weighted by max service sum:")
print(dummy_ps)
# dummy_ps.to_clipboard()

qeia_path = dummy_path + "dummy_qeia.json"
with open(qeia_path, 'r') as f:
    raw_qeia = json.load(f)
    dummy_qeia = QEIAMatrix(raw_qeia)

# Define createDataFrame function - for some reason this doesn't import with QEIAMatrix?
def createDataFrame(self) -> pd.DataFrame:
    # ""Returns a Pandas dataframe representation of this QEIAMatrix

    # Returns:
    #     pd.DataFrame: A dataframe representation of this QEIAMatrix object
    # ""
    row = {}
    
    for option in self.options:
        row[option] = self.options[option].getPriorityModifiers()

    return pd.DataFrame.from_dict(row)


# Convert the dummy QEIA to a dataframe and transpose it to the right orientation
dummy_qeia = dummy_qeia.createDataFrame().transpose()
pd.DataFrame(dummy_qeia)
print("Base dummy QEIA:")
print(dummy_qeia)


def templateToQEIAMultiplier(template: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
    qeia.index.name = 'option'
    qeia.drop(columns=qeia.columns.difference(template.columns), inplace=True)

    # 0 out the template - had to adjust code as wasn't working
    template = template.copy(deep=True)
    template.iloc[:, 2:] = 0.0

    for column in qeia.columns:
        for option in qeia.index:
            if option in template['Option'].unique():
                # Had to adjust this code as pd.IndexSlice was returning an error
                template.loc[template['Option'] == option, column] = qeia.loc[option, column]

    return template


def calculateMCDAForPriorityScoresWithEligibility(priorityScores: pd.DataFrame, qeia: QEIAMatrix) -> pd.DataFrame:
    # ""Calcualate the MCDA outputs for a supplied set of priority scores, QEIA matrix and eligibility table

    # Args:
    #     priorityScores (pd.DataFrame): Dataframe containing the priority scores for each input polygon ID
    #     qeia (QEIAMatrix): The QEIA matrix to use for this MCDA calculation

    # Returns:
    #     pd.DataFrame: A finalised MCDA table with total/rank for each input polygon ID
    # ""
    
    qeiaMultiplier = templateToQEIAMultiplier(priorityScores, qeia)

    # Adjusted the following as original script without iloc did not work due to character columns:
    mcda = priorityScores.copy(deep=True)
    mcda.iloc[:, 2:] = priorityScores.iloc[:, 2:].mul(qeiaMultiplier.iloc[:, 2:])
    mcda['total'] = mcda.iloc[:, 2:].sum(axis=1)
    mcda['rank'] = mcda.groupby('Parcel')['total'].rank(method='first', ascending=False)

    return mcda.sort_values(['Parcel', 'rank'])

## Create alternative dummy QEIAs for testing ------------------------------

# Rescaled -1 to 1 - just divide by 3
qeia_downweighted = dummy_qeia / 3
print("Downweighted QEIA - divided by 3:")
print(qeia_downweighted)
# qeia_downweighted.to_clipboard()

# Rescale without any strength - only 3 possible values: -1, 0, 1
qeia_nostrength = np.sign(dummy_qeia)
print("No strength QEIA - just values of -1, 0, 1")
print(qeia_nostrength)
# qeia_nostrength.to_clipboard()

# Smaller impact - rescale so that:
# 0 = 0.0
# 1 = 0.75
# 2 = 1.0
# 3 = 1.25
# Because this actually changes the distance between weights, this should have an effect on final
# scores/rankings unlike dividing by 3 which keeps the ratios between impact scores.
# This could be an option if we still wanted to have QEIA impact scores, but wanted them to have a 
# smaller effect on outputs (either because we don't have full confidence in them or it makes outputs
# more sensible)

"""""
qeia_smallerimpact = dummy_qeia.replace({1.0 : 0.75, 2.0 : 1.0, 3.0 : 1.25,
                                         -1.0 : -0.75, -2.0 : -1.0, -3.0 : -1.25})
"""
# Tested the above version but this did not have enough difference to change the action order 

# Test with even smaller impact range: 
# 0 = 0.0
# 1 = 1.0
# 2 = 1.1
# 3 = 1.2
qeia_smallerimpact = dummy_qeia.replace({1.0 : 1.0, 2.0 : 1.1, 3.0 : 1.2,
                                         -1.0 : -1.0, -2.0 : -1.1, -3.0 : -1.2})
print("Smaller impact QEIA:")
print(qeia_smallerimpact)
# qeia_smallerimpact.to_clipboard()

# ## Run dummy tests with QEIAs --------------------------------------------------

dummy_mcda_0 = calculateMCDAForPriorityScoresWithEligibility(priorityScores=dummy_ps, qeia=dummy_qeia)
print("DUMMY MCDA - 0: -----------------------------------------------")
print(dummy_mcda_0)
# dummy_mcda_0.to_csv(dummy_path + "Results/Fixed_QEIA/Dummy_MCDA_0_weightedPS.csv")

dummy_mcda_downweighted = calculateMCDAForPriorityScoresWithEligibility(priorityScores=dummy_ps, qeia=qeia_downweighted)
print("DUMMY MCDA - DOWNWEIGHTED: -------------------------------------")
print(dummy_mcda_downweighted)
# dummy_mcda_downweighted.to_csv(dummy_path + "Results/Fixed_QEIA/Dummy_MCDA_Downweighted_weightedPS.csv")

dummy_mcda_nostrength = calculateMCDAForPriorityScoresWithEligibility(priorityScores=dummy_ps, qeia=qeia_nostrength)
print("DUMMY MCDA - NO STRENGTH: --------------------------------------")
print(dummy_mcda_nostrength)
# dummy_mcda_nostrength.to_csv(dummy_path + "Results/Fixed_QEIA/Dummy_MCDA_NoStrength_weightedPS.csv")

dummy_mcda_smallerimpact = calculateMCDAForPriorityScoresWithEligibility(priorityScores=dummy_ps, qeia=qeia_smallerimpact)
print("DUMMY MCDA - SMALLER IMPACT: -----------------------------------")
print(dummy_mcda_smallerimpact)
# dummy_mcda_smallerimpact.to_csv(dummy_path + "Results/Fixed_QEIA/Dummy_MCDA_SmallerImpact_weightedPS.csv")

## PART 3: TESTING SERVICE GROUPINGS ######################################################################################################################################################
print("TESTING: SERVICE GROUPINGS =================================================================================")

# This investigation is specifically looking at the implications of having 1/niES (i.e. 1 / number of indicators in each
# service) as a multiplier, to downweight services with more indicators
# We want to see if using or not using these groupings is expected to have a large impact on final scores

print("TEST 1: No service grouping (just MCDA 0) --------------------------------------------")
service_test1_mcda = calculateMCDAForPriorityScoresWithEligibility(priorityScores=dummy_ps, qeia=dummy_qeia)
print(service_test1_mcda)
# service_test1_mcda.to_csv(dummy_path + "Results/Fixed_QEIA/Service_Test1_MCDA.csv")

print("TEST 2: Service weightings from dummy priority scores --------------------------------")

service_test = dummy_ps.copy(deep=True)

# Get unique services present
services = list(set([i.split("_")[1] for i in data_columns]))
print("All services:", services)

for i in services:
    print("Service: ", i)
    service_columns = list(filter(lambda k: i in k, data_columns))
    print("Service columns: ", service_columns)
    print("Number of indicators: ", len(service_columns))

    # The final multiplier would be (1/n(ES))/n(iES), but for testing keeping it to just 1/n(iES) for easier evaluation of results
    # (the 1/nES would not make a difference to rankings as it is a constant)
    print("( 1/", len(service_columns), ")")
    multiplier = (1/ len(service_columns))
    print(multiplier)

    service_test[service_columns] = service_test[service_columns].apply(lambda row: multiplier * row)

print(service_test)
# service_test.to_clipboard()

service_test2_mcda = calculateMCDAForPriorityScoresWithEligibility(service_test, dummy_qeia)
print(service_test2_mcda)
# service_test2_mcda.to_clipboard()
# service_test2_mcda.to_csv(dummy_path + "Results/Fixed_QEIA/Service_Test2_MCDA.csv")

print("TEST 3: Service weightings with test recategorisation ---------------------------------------------")

# Read in recategorised version of dummy priority scores - this version has NDeposition under
# the AirP service group instead of Biod

dummy_ps_recat = pd.read_csv(dummy_path + "Dummy_Data_2_TestRecategorise.csv")
print("Alternative dummy PS with recategorised NDeposition:")
print(dummy_ps_recat)

# Apply parcel level normalisation to recategorised dummy PS
data_columns_recat = dummy_ps_recat.columns.difference(['Parcel', 'Option'])
dummy_ps_recat['serviceSum'] = dummy_ps_recat[data_columns_recat].sum(axis=1)
dummy_ps_recat['max_serviceSum'] = dummy_ps_recat.groupby(['Parcel'])['serviceSum'].transform("max")
weighting_columns_recat = dummy_ps_recat.columns.difference(['Parcel', 'Option', 'serviceSum'])
dummy_ps_recat[weighting_columns_recat] = dummy_ps_recat[weighting_columns_recat].apply(lambda row: row / row['max_serviceSum'], axis=1)
dummy_ps_recat.drop(columns=['serviceSum', 'max_serviceSum'], inplace=True)

services_recat = list(set([i.split("_")[1] for i in data_columns_recat]))

for i in services_recat:
    print("Service: ", i)
    service_columns = list(filter(lambda k: i in k, data_columns_recat))
    print("Service columns: ", service_columns)
    print("Number of indicators: ", len(service_columns))

    # The final multiplier would be (1/n(ES))/n(iES), but for testing keeping it to just 1/n(iES) for easier evaluation of results
    # (the 1/nES would not make a difference to rankings as it is a constant)
    print("( 1/", len(service_columns), ")")
    multiplier = (1/ len(service_columns))
    print(multiplier)

    dummy_ps_recat[service_columns] = dummy_ps_recat[service_columns].apply(lambda row: multiplier * row)

print(dummy_ps_recat)
# dummy_ps_recat.to_clipboard()

service_test3_mcda = calculateMCDAForPriorityScoresWithEligibility(dummy_ps_recat, dummy_qeia)
# service_test3_mcda.to_csv(dummy_path + "Results/Fixed_QEIA/Service_Test3_MCDA.csv")