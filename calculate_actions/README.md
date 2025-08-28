# Calculate Actions

A set of scripts to calculate the priority and eligible actions for given polygons

## Configuration

### Layer Config

There is a template file for layer configuration `layers.json.template`, this contains configuration and file paths to 
data layers used by this tool. The file will be split into two main sections, priority_layers andeligibility_layers in 
the form:

```json
{
    "priority_layers": {
        "unique_layer_id": {
            "layer_name": "Human friendly name",
            "filepath": "path/to/file.ext",
            "type": "vector"  // or "raster" for raster files
        },
        ...
    },
    "eligibility_layers": {
        "unique_layer_id": {
            "layer_name": "Human friendly name",
            "filepath": "path/to/file.ext",
            "type": "vector"  // or "raster" for raster files
        },
        ...
    }
}
```

All layers need to be in the same projection for the scripts to work correctly.

#### Priority Layers

For each prority layer an entry should be added under the `priority_layers` object in the configuation JSON file, this
can be a vector (i.e. `.gpkg`) or a raster file (i.e. `.tif`). Each needs to have a unqiue ID label and should have a 
unique `layer_name` and `filepath`.

Priority layer labels should be in the form of `Priority_{EcosystemServiceGroup}_{Action}` where EcosystemServiceGroup is the
abbreviated name of the ecosystem service group (i.e. `Biod` for Biodiversity) and Action is the abbreviated name of the action
(i.e. `MaintainSNH` for Maintain Semi-Natural Habitats).

#### Eligibility Layers

For each prority layer an entry should be added under the `priority_layers` object in the configuation JSON file, this
can be a vector (i.e. `.gpkg`), currently raster eligibilty layers are not supported. Each needs to have a unqiue ID 
label and should have a unique `layer_name` and `filepath`.

Eligibility layer labels currently do not have a specific format, but should be short, unique and descriptive of the layer, i.e.
`GS6`, `LH1`, `SW17`, `SW18` etc.

### Column Aggregation

There are some priority layers that should be aggregated together to prevent them from There is a template file for column aggregation `column_aggregation.json.template`, this contains an example of how to 
aggregate the values of the priority layers for each polygon, this is in the form:

```json
{
    {
        "priority_layer_group_label": {
            "operation": "MAX",
            "options": {   
                "eligibility_option_label": [
                    "priority_layer_group_item_label",
                    ...
                ],
                ...
            }
        },
        ...
    }
}
```

Where each line the `priority_layer_group_label` matches an entry in the pattern for a group of priority layers  in the config 
file described above.

For example if you have a group of priority layers that are all related to maintainging semi-natural habitats, you could have a 
group label of `Priority_Biod_MaintainSNH` (`Biod` being the ecosystem service group, `MaintainSNH` being the action) and then have a
set of Priority Layers such as `Priority_Biod_MaintainSNH_LCG`, `Priority_Biod_MaintainSNH_BBG` etc. which could present as;

```json
{
    "Priority_Biod_MaintainSNH": {
        "operation": "MAX",
        "options": {
            "OPT1": [
                "LCG"
            ],
            "OPT2": [
                "LCG",
                "BBG"
            ]
        }
    }
}
```

The `operation` can be one of `MAX`, `MIN`, `AVG` more operations may be added in the future, but the commonly used one is currently 
`MAX` to get the maximum value for each polygon across the priority layers in the group.

### Weightings

There is a template file for layer configuration `weightings.json.template`, this contains weightings that will be applied
to the extracted priority scores for each input polygon in the form:

```json
    {
        "priority_layer_label": 1.23,
        ...
    }
```

Where each line the `priority_layer_label` matches an entry in the Priority Layers config file described above.

### QEIA matrix

This is a transformative matrix that defines the modifier to use for each eligible option for each polygon, there is 
a template example at `qeia.json.template` where data is of the form:

```json
{
    "eligibility_layer_label": {
        "priority_layer_label": -3,
        ...
    },
    ...
}

```

Where the `eligibility_layer_label` matches an entry in the Eligibility section of the Layers config file defined above
and `priority_layer_label` matches an entry in Priority Layer section of the Layers config file.

The value should be an integer between -3 and 3 (this is not enfored at present), it also support `null` values to indicate
a not assesed or unknown impact value.

## Create local virtual environment

From the `calculate_actions` folder

### Linux

To create a virtual environment to put dependencies into you can run the following;

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows

To create a virtual environment under windows to put dependencies into you can run the following under command prompt;

```bash
python -m venv .venv
```
Enter the virtual environment from the same folder that you installed the virtualenv file into

```bash
.venv\Scripts\activate.bat
```

You should have the name `(.venv)` prepended to your command prompt window to show you are in the virtual environment i.e.;

`(.venv) C:\Repositories\future-land-use\calculate_actions>`

Then install the required packages;

```bash
python -m pip install -r requirements.txt
```

To leave the virtual environment close the window or use `deactivate`

**NOTE**: You can potentially run this via powershell, but frequently system admins will lock down running powershell 
scripts (`activate.ps1`).

## Process single polygon

To run locally with a single polygon, enter the virtual environment you created and run the script;

```bash
python calculate_actions_for_single_input.py -i 1234567 -p 1234567.wkt -l layers.json -w weighting.json -q qeia.json
```

 - `-i / --polyid` - Unique ID for the polygon
 - `-p / --polygon_wkt` - Path to WKT file containing polygon geometry
 - `-l / --layer_config` - Path to JSON file containing priority and eligibility layers
 - `-w / --weightings_config`- Path to JSON file containing priority weightings
 - `-q / --qeia_matrix` - Path to JSON file containing QEIA matrix
 - `-o / --output` - (Optional) Path to store MCDA output to as a `.csv` file

This script is designed to run a single polygon through the relevant steps to provide an output
for testing or validation purposes. By default the script will print out a representation of the data
but the output can be saved to a file using the `-o` switch.

## Process multiple polygons

To run locally with multiple polygons, enter the virtual environment you careated and run the script;

```bash
python calculate_actions_for_multiple_inputs.py -i polygons.pkg -l layers.json -w weightings.json -q qeia.json --priority_score_output_path priority_scores.csv --weighted_priority_score_output_path weighted_priority_scores.csv --eligibility_options_output_path eligibility.csv --mcda_output_path mcda.csv
```

This will output a CSV with the MCDA output to `mcda.csv` as well as intermediate priority / weighted priority scores and an eligiblity option table that can be used in the script as precalculated inputs, the full list of inputs are described below;

 - `-i / --poly_source {path}` - Path to polygon datasource, ideally a GeoPackage, but should function with any vector format
 - `-c / --polygon_id_column {name}` - [**Optional**] allows user to specify the attribute column name to use as an ID for polygons [Default: NGC]
 - `-l / --layer_config {path}` - Path to JSON file containing priority and eligibility layers
 - `-w / --weightings_config {path}`- Path to JSON file containing priority weightings
 - `-q / --qeia_matrix {path}` - Path to JSON file containing QEIA matrix
 - `--precalculated_priority_scores {path}` - [**Optional**] Path to CSV containing precalculated priority scores (skipping priority score calcuation step if this argument is present)
 - `--priority_score_output_path {path}` - [**Optional**] Path to store calculated priority scores out to as CSV [Default: `priority_scores.csv`]
 - `--overwrite_priority_score_output` - [**Optional**] Overwrite priority score output if it exists [Default: False]
 - `--precalculated_weighted_priority_scores {path}` - [**Optional**] Path to CSV containing precalculated weighted priority scores (skipping priority and weighted priority score calculations stpes if argument is present)
 - `--weighted_priority_score_output_path {path}` - [**Optional**] Path to store calculated weighted priority scores out to as CSV [Default: `weighted_priority_scores.csv`]
 - `--overwrite_weighted_priority_score_output` - [**Optional**] Overwrite weighted priority score output if it exists [Default: False]
 - `--precalculated_eligibility {path}` - [**Optional**] Path to CSV containing precalculated eligiblity options for polygons (skipping eligibility option step if this argument is present)
 - `--precalculated_eligibility_as_area {path}` - [**Optional**] Path to CSV containing precalculated eligiblity options as area for polygons (skipping eligibility option step if this argument is present)
 - `--eligibility_options_output_path {path}` - [**Optional**] Path to store calculated eligibilty options as CSV [Default: `eligibility.csv`]
 - `--overwrite_eligiblity_output` - [**Optional**] Overwrite eligibility option output if it exists [Default: False]
 - `--column_group_config_path` - [**Optional**] Path to a JSON file containing a configuration object for column group aggregation, if blank, no aggregation will be performed [Default: ]
 - `--active_services_matrix_path` - [**Optional**] Path to output active services matrix as CSV for this run, if blank dont write [Default: ]
 - `--mcda_output_path {path}` - [**Optional**] Path to store output CSV of the MCDA analysis step [Default: `mcda.csv`]
 - `--overwrite_mcda_output` - [**Optional**] Overwrite MCDA output if it exists [Default: False]

You can use the `--precalculated_x` arguments to input previously run outputs for the relevant steps to speed up processing while adjusting elements of the inputs.

## Utility Scripts

### Test Score Calculation

We have included a basic test set of data to do a simple test of the score calculation, this can be run with the following command;

```bash
python calculate_actions_for_multiple_inputs.py -c id -i ./testing/precalculated/layers.json  -l ./testing/precalculated/layers.json -w ./testing/precalculated/weightings.json -q ./testing/precalculated/qeia.json --precalculated_priority_scores ./testing/precalculated/priority_scores.csv --precalculated_eligibility ./testing/precalculated/eligibility_options.csv --column_group_config_path ./testing/precalculated/column_aggregation.json --active_services_matrix_path ./testing/precalculated/active_services_matrix.csv --mcda_output_path ./testing/precalculated/mcda.csv --overwrite_mcda_output --overwrite_weighted_priority_score_output
```

### Generate Column Aggregation Templates

Run the utility script `utility/generate_column_aggregation_templates.py` to generate a template for column aggregation based on the layers in the configuration file.

```bash
python utility/generate_column_aggregation_templates.py -a maintain_snh.csv -o Priority_Biod_MaintainSNH
```

 - `-a / --aggregation_config` - Path to CSV file containing column aggregation configuration as a TRUE/FALSE matrix outlined below
 - `'-n / --aggregation_name` - Name of the aggregation to generate, this will be used as the key in the output JSON file i.e. `Priority_Biod_MaintainSNH`

The input CSV file should be in the form of a TRUE/FALSE matrix where each row is an eligibility option and each column is a priority layer code (that will be appended to the aggregation name to create
the full priority layer ID), with `TRUE` indicating that the priority layer should be included in the aggregation for that option and `FALSE` indicating it should not. For example:

```csv
option,ASN,BLB,LCG,...
OPT1,TRUE,FALSE,FALSE,...
OPT2,FALSE,TRUE,FALSE,...
OPT3,FALSE,FALSE,TRUE,...
```
In this example, `ASN`, `BLB`, and `LCG` are the priority layers options and `OPT1`, `OPT2`, and `OPT3` are the eligibility options. The output will be a JSON object with the aggregation configuration 
for each option.

i.e.

```json
{
    "Priority_Biod_MaintainSNH": {
        "operation": "MAX",
        "options": {
            "OPT1": [
                "ASN"
            ],
            "OPT2": [
                "BLB"
            ],
            "OPT3": [
                "LCG"
            ]
        }
    }
}
```

Currently the only operation supported is `MAX`, but this may be extended in the future.

### Generate Layer Configuration Template

Run the utility script `utility/generate_layer_config_template.py` to generate a template for layer configuration based on the layers in the configuration file.

```bash
python utility/generate_layer_config_template.py -p layers.csv -e eligibility.csv -o layers.json --priority_base_path /path/to/priority/layers --eligibility_base_path /path/to/eligibility/layers --prefer_raster
```

 - `-p / --priority_input` - Path to CSV file containing priority layer configuration
 - `-e / --eligibility_input` - Path to CSV file containing eligibility layer configuration
 - `-o / --output` - Path to output JSON file for layer configuration
 - `--priority_base_path` - [**Optional**] Base path to replace found priority paths in the output JSON file
 - `--eligibility_base_path` - [**Optional**] Base path to replace found eligibility paths in the output JSON file
 - `--prefer_raster` - [**Optional**] If set, will prefer raster layers over vector layers when generating the template, default is False

The input CSV files should be in the form of a list of layers with the following columns:

```csv
service_indicator/option_code,placeholder_file_path,raster_filepath_if_applicable
layer_id,path/to/file.ext,optional/path/to/raster.tif
...
```

Where `service_indicator/option_code` is the human friendly name for the layer, `layer_id` is the unique ID for the layer, and `placeholder_file_path` is the path to the file that will be used as a placeholder in the output JSON file. The `raster_filepath_if_applicable` column is optional and can be used to specify a raster file path if applicable. 

For priority layers the `service_indicator` should be in the form of `Priority_{EcosystemServiceGroup}_{Action}` where `EcosystemServiceGroup` is the abbreviated name of the ecosystem service group (i.e. `Biod` for Biodiversity) and `Action` is the abbreviated name of the action (i.e. `MaintainSNH` for Maintain Semi-Natural Habitats).

For eligibility layers the `option_code` should be a short, unique and descriptive of the layer, i.e. `Eligibility_GS6`, `Eligibility_LH1`, `Eligibility_SW17`, `Eligibility_SW18` etc.

### Generate QEIA Matrix

Run the utility script `utility/generate_qeia_matrix.py` to generate a QEIA matrix based on the layers in the configuration file.

```bash
python utility/generate_qeia_matrix.py -i qeia_input.csv -l layers.json -o qeia.json
```

 - `-i / --qeia_input` - Path to CSV file containing QEIA input data
 - `-l / --layer_config` - Path to JSON file containing priority and eligibility layers
 - `-o / --qeia_output` - [**Optional**] Path to output JSON file for QEIA matrix [Default: `qeia.json`]

Where the input CSV file should be in the form of a list of QEIA inputs with the following columns:

```csv
eligibility_layer_id,priority_layer_id,impact_score
Eligibility_GS6,Priority_Biod_MaintainSNH,1.0
Eligibility_LH1,Priority_Biod_MaintainSNH,-1.0
...
```

### Generate Random QEIA Matrix

Run the utility script `utility/generate_random_qeia_matrix.py` to generate a random QEIA matrix based on the layers in the configuration file.

```bash
python utility/generate_random_qeia_matrix.py -l layers.json -o qeia.json --min_range -3 --max_range 3 --whole_numbers
```
    
 - `-l / --layer_config` - Path to JSON file containing priority and eligibility layers
 - `-o / --qeia_output` - [**Optional**] Path to output JSON file for QEIA matrix [Default: `qeia.json`]
 - `--min_range` - [**Optional**] Minimum range for impact scores, default is -3
 - `--max_range` - [**Optional**] Maximum range for impact scores, default is 3
 - `--whole_numbers` - [**Optional**] If set, will generate whole numbers for impact scores, default is False (i.e. will generate floats)

### Pregenerated Eligibility Options (Force True)

Run the utiltity script `utility/generate_true_eligibility_table.py` to pre generate an options
eligbility table where all polygons are fored to be eligible for all options.

```bash
python utility/generate_true_eligibility_table.py -i polygons.gpkg -c id_column -l layers.json -o eligibility.csv
```

 - `-i / --poly_source {path}` - Path to polygon datasource, ideally a GeoPackage, but should function with any vector format
 - `-c / --polygon_id_column {name}` - [**Optional**] allows user to specify the attribute column name to use as an ID for polygons [Default: NGC]
 - `-l / --layer_config {path}` - Path to JSON file containing priority and eligibility layers
 - `-o / --eligibility_output {path}` - Path to store eligibility output table [Default: `eligibility.csv`]