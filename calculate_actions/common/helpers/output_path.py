from pathlib import Path

def get_output_path(base: str, run_name: str = None, output_path: str = None) -> Path:
    base_path = Path(base)

    if output_path:
        base_path = base_path.joinpath(Path(output_path))
    
    if run_name:
        base_path = base_path.joinpath(Path(run_name))

    if not base_path.exists():
        base_path.mkdir(parents=True)

    return base_path

def get_output_filename(filename: str, run_name: str = None) -> Path:
    if run_name:
        file = Path(filename)
        return file.with_name(f'{file.stem}_{run_name}{file.suffix}')
    return Path(filename)