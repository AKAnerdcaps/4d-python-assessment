import os
import pandas as pd
from datetime import datetime

def validate_field(field_value, field_info):
    """Validates a field based on its schema."""

    field_type = field_info['type']

    # If field is required and missing
    if field_info.get('required', False) and pd.isnull(field_value):
        return False, f"Missing required field: {field_info['name']}"

    # If the field is missing but not required
    if pd.isnull(field_value):
        return True, ""

    # Type Validation    
    if field_type == 'int':
        try:
            int_value = int(field_value)
            return True, ""
        except (ValueError, TypeError):
            return False, f"Invalid type for field: {field_info['name']}. Expected int but got {type(field_value).__name__}"

    elif field_type == 'float':
        try:
            float_value = float(field_value)
            return True, ""
        except (ValueError, TypeError):
            return False, f"Invalid type for field: {field_info['name']}. Expected float but got {type(field_value).__name__}"

    elif field_type == 'string':
        if not isinstance(field_value, str):
            return False, f"Invalid type for field: {field_info['name']}. Expected string but got {type(field_value).__name__}"

    elif field_type == 'enum':
        if field_value not in field_info['values']:
            return False, f"Invalid value for field: {field_info['name']}. Expected one of {field_info['values']} but got {field_value}"

    elif field_type == 'date':
        try:
            datetime.strptime(field_value, field_info['format'])
        except ValueError:
            return False, f"Invalid date format for field: {field_info['name']}. Expected format {field_info['format']} but got {field_value}"
    
    return True, ""

def validate_data(schema, dataframe):
    error_reports_folder = "./error_reports"
    os.makedirs(error_reports_folder, exist_ok=True)
    error_rows = []
    clean_rows = []

    for _, row in dataframe.iterrows():
        record = row.to_dict()
        row_errors = []

        for field_info in schema:
            field_name = field_info['name']
            field_value = record.get(field_name)

            is_valid, error_message = validate_field(field_value, field_info)
            if not is_valid:
                row_errors.append(error_message)

        if row_errors:
            record['errors'] = row_errors
            error_rows.append(record)
        else:
            clean_rows.append(record)

    error_df = pd.DataFrame(error_rows)
    clean_df = pd.DataFrame(clean_rows)

    # Cast to expected type, avoid issues with arrow
    for field in schema:
        field_name = field['name']
        field_type = field['type']
        
        if field_name in clean_df.columns:
            if field_type == 'float':
                clean_df[field_name] = pd.to_numeric(clean_df[field_name], errors='coerce')
            elif field_type == 'int':
                clean_df[field_name] = pd.to_numeric(clean_df[field_name], errors='coerce').astype('Int64')
            elif field_type == 'string':
                clean_df[field_name] = clean_df[field_name].astype(str)
            elif field_type == 'date':
                clean_df[field_name] = pd.to_datetime(clean_df[field_name], format=field.get('format', '%Y-%m-%d'), errors='coerce')

    return clean_df, error_df