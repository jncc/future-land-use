import pandas
import json
from pprint import pprint 

qeia_matrix_csv_path = "../../OFF-SEN_Offers_QEIA_all_scores_and_links_UPDATEDMar2025.csv"
service_indicator_mapping_path = "../../qeia_service_mapping.json.template"
layers_path = "../../layers.json.template"
qeia_matrix = pandas.read_csv(qeia_matrix_csv_path,  usecols=['action_code', 'sfi_code', 'action', 'service_indicator', 'impact_score'])

with open(service_indicator_mapping_path, 'r') as f:
    data = json.load(f)
    
service_indicator_mapping = pandas.DataFrame(data)

#filter out rows where both service_indicator and action_code are null
qeia_matrix = qeia_matrix.dropna(subset=['service_indicator', 'action_code'], how='all')

qeia_layer_matrix = qeia_matrix.merge(service_indicator_mapping, 
                            on='service_indicator', 
                            how='inner')

qeia = {}

# itterate through each row in qeia_layer_join_matrix
for index, row in qeia_layer_matrix.iterrows():
    # if action_code is null, set action_code to service_indicator
    if pandas.isnull(row['action_code']):
        qeia_layer_matrix.at[index, 'action_code'] = row['service_indicator']
    
    # return action_code, service_indicator and impact_score as json object
    
    # qeia.update({
    #     row['action_code']: {
    #         'layer': row['layer'],
    #         'service_indicator': row['service_indicator'],
    #         'impact_score': row['impact_score']
    #     }
    # })
    
    qeia.update({
        row['action_code']: {
            row['layer'] : row['impact_score']
        }
    })
    
pprint(qeia)

# print(qeia_matrix.columns)
# # print data type info from cols
# print(qeia_matrix.dtypes)
# # print first 5 rows
# print(qeia_matrix.head())
# # print last 5 rows
# print(qeia_matrix.tail())
# #print specific row
# print(qeia_matrix.iloc[98])
# # print summary statistics
# print(qeia_matrix.describe())

# print(service_indicator_mapping.head())

print(qeia_layer_matrix)

