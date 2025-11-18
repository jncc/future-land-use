from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)
logger.setLevel("INFO")

def get_output_path(base: str, run_name: str = None, output_path: str = None) -> Path:
    base_path = Path(base)

    if output_path:
        base_path = base_path.joinpath(Path(output_path))
    
    if run_name:
        base_path = base_path.joinpath(Path(run_name))

    if not base_path.exists():
        logger.info(f'Creating output directory at: {base_path}')
        base_path.mkdir(parents=True)
    else:
        logger.warning(f'Output directory already exists at: {base_path}')

    return base_path

def get_output_filename(filename: str, run_name: str = None) -> Path:
    if run_name:
        file = Path(filename)
        return file.with_name(f'{file.stem}_{run_name}{file.suffix}')
    return Path(filename)