import argparse
import logging
from pathlib import Path

import pyarrow.csv as pacsv
import pyarrow.parquet as pq

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(asctime)s: %(message)s'
)

def main(input_root: str, prefix: str, output_file: str, overwrite: bool) -> int:
    input_root_path = Path(input_root).resolve()
    output_path = Path(output_file).resolve()
    output_format = output_path.suffix.lower().lstrip('.')

    if output_format not in {'csv', 'parquet'}:
        logging.error(f'Output filename must end in .csv or .parquet: {output_path}')
        return 1

    tile_paths = sorted(input_root_path.glob(f'*/{prefix}_*.csv'))
    tile_paths = [path for path in tile_paths if path.resolve() != output_path.resolve()]

    if not tile_paths:
        logging.error(f'No {prefix}_*.csv files found under {input_root_path}')
        return 1
    if output_path.exists() and not overwrite:
        logging.error(f'{output_path} already exists; use --overwrite to replace it')
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(output_path.name + '.tmp')
    writer = None
    total_rows = 0
    logging.info(f'Merging {len(tile_paths)} files with prefix {prefix} into {output_path}')
    try:
        for path in tile_paths:
            table = pacsv.read_csv(path)
            if writer is None:
                if output_format == 'parquet':
                    writer = pq.ParquetWriter(tmp_path, table.schema, compression='zstd')
                else:
                    writer = pacsv.CSVWriter(tmp_path, table.schema)
            writer.write_table(table)
            total_rows += table.num_rows
            logging.info(f'  {path.parent.name}: {table.num_rows} rows')
    except Exception:
        if writer is not None:
            writer.close()
        tmp_path.unlink(missing_ok=True)
        raise

    writer.close()
    tmp_path.replace(output_path)
    logging.info(f'Wrote {total_rows} rows from {len(tile_paths)} files to {output_path}')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge per-tile CSV outputs into one table')
    parser.add_argument('-i', '--input-root', type=str, required=True, help='Directory containing per-tile CSV files')
    parser.add_argument('-p', '--prefix', type=str, default='mcda', help='Filename prefix to find and merge')
    parser.add_argument('-o', '--output-file', type=str, required=True, help='Merged output path ending in .csv or .parquet')
    parser.add_argument('--overwrite', action=argparse.BooleanOptionalAction, default=False, help='Overwrite an existing merged output')

    args = parser.parse_args()
    main(args.input_root, args.prefix, args.output_file, args.overwrite)
