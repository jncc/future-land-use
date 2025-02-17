To run locally:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python calculate_actions.py --poly_id 1234567 --wkt 1234567.wkt --data_dir /path/to/layers/dir --layer_config layers.json --priority_weightings weightings.csv --qeia_matrix qeia.csv