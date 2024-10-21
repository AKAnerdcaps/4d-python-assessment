from src.utils.logger import sys_logger
import pandas as pd
import os

def get_file_date(filename):
    date = filename.split("_")[-1].split(".")[0]
    return pd.to_datetime(date)

def get_files_to_process(path, last_run_date):
    sys_logger.info(f"Getting files to process from {path}")
    files = os.listdir(path)
    if last_run_date:
        files = [f for f in files if get_file_date(f) > last_run_date]    
    sys_logger.info(f"Found {len(files)} files to process")
    return files

def get_save_filename(source_name):
    sys_logger.info(f"Getting save filename for {source_name}")
    return f"./final_data/{source_name}.parquet"

def get_error_filename(source_name, date):
    sys_logger.info(f"Getting error filename for {source_name}")
    return f"./error_reports/errors_{source_name}_{date}.csv"

def save_file(filepath, dataframe):
    sys_logger.info(f"Saving file with {len(dataframe)} rows to {filepath}")
    dataframe.to_parquet(filepath, index=False)

def read_csv(filepath, **kwargs):
    sys_logger.info(f"Reading csv file from {filepath} with kwargs {kwargs}")
    return pd.read_csv(filepath, **kwargs)

def read_excel(filepath, **kwargs):
    sys_logger.info(f"Reading excel file from {filepath} with kwargs {kwargs}")
    return pd.read_excel(filepath, **kwargs)

def read_parquet(filepath):
    sys_logger.info(f"Reading parquet file from {filepath}")
    return pd.read_parquet(filepath)

def read_json(filepath, **kwargs):
    sys_logger.info(f"Reading json file from {filepath} with kwargs {kwargs}")
    return pd.read_json(filepath, **kwargs)

def get_read_func(type):
    match type:
        case "csv":
            return read_csv
        case "excel":
            return read_excel
        case "parquet":
            return read_parquet
        case "json":
            return read_json
        case _:
            raise ValueError(f"Unsupported file type: {type}")
    
def get_saved_file(source_name):
    sys_logger.info(f"Getting saved file for {source_name}")
    filepath = get_save_filename(source_name)
    try:
        file = read_parquet(filepath)
    except FileNotFoundError:
        sys_logger.warning(f"File not found at {filepath}. Creating new file")
        file = pd.DataFrame()
    sys_logger.info(f"{source_name} file has {len(file)} rows")
    return file