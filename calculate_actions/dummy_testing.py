import pandas as pd
import numpy as np

dummy_path = "O:/EAT/Ecosystems Analysis/ELMs/Spatial Prioritisation v2.0/Data/MCDA Workflow Data/MCDA Change Tests/dummy_data/Dummy_Data_For_Weightings.csv"
dummy_ps = pd.read_csv(dummy_path)
print("Dummy dataframe read in:")
print(dummy_ps)

# Initial priority score weighting function code - creates a list of data columns
data_columns = dummy_ps.columns.difference(['Parcel', 'Option', 'Active Service Sum'])
print("Data columns:")
print(data_columns)

# 1/n(ES) code - comment out as not relevant to option level fix
# priorityScores = dummy_ps.apply(lambda row: (1 / row['Active Service Sum']) * row[data_columns], axis=1)
# print("priorityScores after lambda:")
# print(priorityScores)
priorityScores = dummy_ps
priorityScores['serviceSum'] = priorityScores[data_columns].sum(axis=1)
print("priorityScores:")
print(priorityScores)
priorityScores = priorityScores.apply(lambda row: row[data_columns] / row['serviceSum'], axis=1)
print("priorityScores return:")
print(priorityScores) 

# From calculate priority score weighting function:
# Normalise the scores to ensure they sum to 1
print("Normalise code:")
priorityScores['total'] = priorityScores.sum(axis=1)
print(priorityScores)

priorityScores = priorityScores.apply(lambda row: row / row['total'], axis=1)
print("apply lambda")
print(priorityScores)

# ALTERNATIVE 1: Instead of dividing by service sum per row, divide by the maximum
# service sum per parcel to get the same weighted priority score for layers present
# in all options per parcel
# (This only affects the outputs in cases where there has been a lookup with SNH indicators
# as they are the only ones that will have nulls for some options and priority scores for others)
alt_pS = dummy_ps
alt_pS['serviceSum'] = alt_pS[data_columns].sum(axis=1)
alt_pS['max_serviceSum'] = alt_pS.groupby(['Parcel'])['serviceSum'].transform("max")
print("Max service sum:")
print(alt_pS)

alt_pS_out = alt_pS.apply(lambda row: row[data_columns] / row['max_serviceSum'], axis=1)
print("Divide by max service sum:")
print(alt_pS_out)

# ALTERNATIVE 2: Group the weightings by services (so they sum to 1 within a service
# area)
print("ALTERNATIVE 2")
alt_pS_2 = alt_pS
# Get unique services present
services = list(set([i.split("_")[1] for i in data_columns]))
print(services)
# unique_services = list(set(services))
# print(unique_services)

for i in services:
    print("Service: ", i)
    service_columns = list(filter(lambda k: i in k, data_columns))
    print("Service columns: ", service_columns)

    alt_pS_2['service_sum'] = alt_pS_2[service_columns].sum(axis=1)
    alt_pS_2['service_sum'] = alt_pS_2.groupby(['Parcel'])['service_sum'].transform("max")

    service_columns.append("service_sum")
    alt_pS_2[service_columns] = alt_pS_2[service_columns].apply(lambda row: row / row['service_sum'], axis = 1)
    alt_pS_2.drop(columns=['service_sum'], inplace=True)

    print(alt_pS_2)

alt_pS_2.drop(columns=['serviceSum', 'max_serviceSum'], inplace=True)
print("Weighted per service:")
print(alt_pS_2)

# This wouldn't generally be recommended to be used as the final priority score
# in an MCDA without being made to sum to 1, but in order to test whether the last
# 1/n(ES) step is having an effect this will be done

# ALTERNATIVE 3: Use 1/n(ES) to have all present priority scores per parcel add to 1
# and make the MCDA follow the simple additive weighting (SAW) approach

# The active service sum calculation will need to be ammended to make sure it is
# summing services, not indicators

print("ALTERNATIVE 3")
alt_pS_3 = alt_pS_2
alt_pS_3 = alt_pS_3.apply(lambda row: (1 / row['Active Service Sum']) * row[data_columns], axis=1)
print("1/n(ES) applied:")
print(alt_pS_3)

# ALTERNATIVE 4: Using Rory's suggestion of multiplying by (1/n(ES))/n(EiS) per service
# to adjust scores for services with more indicators

print("ALTERNATIVE 4")
# zPS/sum(zPS) with parcel weighting fix

alt_pS_4 = alt_pS
print(alt_pS_4)
# Add another column to test df with an inactive service for one of the parcels
alt_pS_4['Priority_Biod_TestInd'] = [1.0, 1.0, 1.0, float("nan"), float("nan"), float("nan")]
print("Initial data:")
print(alt_pS_4)

alt_pS_4['serviceSum'] = alt_pS_4[data_columns].sum(axis=1)
alt_pS_4['max_serviceSum'] = alt_pS_4.groupby(['Parcel'])['serviceSum'].transform("max")
print(alt_pS_4)
data_columns = alt_pS_4.columns.difference(['Parcel', 'Option', 'Active Service Sum'])
print("Data columns: ", data_columns)
alt_pS_4[data_columns] = alt_pS_4[data_columns].apply(lambda row: row[data_columns] / row['max_serviceSum'], axis=1)
alt_pS_4.drop(columns=['Active Service Sum', 'serviceSum', 'max_serviceSum'], inplace=True)
print("Parcel weighting:")
print(alt_pS_4)
print("n(ES) = ", len(services))

alt_pS_4.groupby(['Parcel'])
""" print("Grouped:")
print(alt_pS_4) """

for i in services:
    print("Service: ", i)
    service_columns = list(filter(lambda k: i in k, data_columns))
    print("Service columns: ", service_columns)
    print("Number of indicators: ", len(service_columns))

    print("( 1/", len(services), " / ", len(service_columns), ")")
    multiplier = ((1/len(services)) / len(service_columns))
    print(multiplier)

    alt_pS_4[service_columns] = alt_pS_4[service_columns].apply(lambda row: multiplier * row)

print(alt_pS_4)
