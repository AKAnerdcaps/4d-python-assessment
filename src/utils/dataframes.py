from src.utils.logger import sys_logger
from src.utils.constants import SYSTEM_COLS
from src.utils.files import get_saved_file, save_file, get_save_filename, get_error_filename
from src.utils.validation import validate_data
import pandas as pd
from uuid import uuid4


def apply_scd2(old_df, new_df, key_cols, date, is_full=False):
    """
    Apply Slowly Changing Dimension Type 2 logic to a dataframe

    Parameters
    ----------
    old_df : pd.DataFrame
        The current state of the dataframe
    new_df : pd.DataFrame
        The new state of the dataframe
    key_cols : list
        The columns to use as the primary key
    date : pd.Timestamp
        The effective date for the new records
    is_full : bool, optional
        Whether the new dataframe is a full load, by default False

    Returns
    -------
    pd.DataFrame
        The updated dataframe with SCD2 applied
    """

    old_file = old_df.copy()
    new_file = new_df.copy()

    for df in [old_file]:
        if "is_current" not in df.columns:
            df["is_current"] = True
        if "expiry_date" not in df.columns:
            df["expiry_date"] = pd.to_datetime("2099-12-31")
            df["expiry_date"].astype("datetime64[ns]", copy=False)
        if "effective_from" not in df.columns:
            df["effective_from"] = date
            df["effective_from"].astype("datetime64[ns]", copy=False)
    if key_cols is not None:
        for column in key_cols:
            if column not in old_file.columns:
                old_file[column] = None

    sys_logger.info(f"Processing file with {len(new_file)} records.")

    if "hash" not in old_file.columns:
        old_file["hash"] = pd.util.hash_pandas_object(
            old_file.drop(columns=SYSTEM_COLS, errors="ignore"),
            index=False,
        )
    new_file["hash"] = pd.util.hash_pandas_object(
        new_file.drop(columns=SYSTEM_COLS, errors="ignore"), index=False
    )
    old_file["index"] = old_file.index
    new_file["index"] = new_file.index

    if is_full:
        # slightly faster approach for full file loads
        merged = pd.merge(
            old_file[old_file["is_current"]],
            new_file,
            on=["hash"],
            how="outer",
            suffixes=["", "_new"],
            indicator=True,
        )
        old = merged[merged["_merge"] == "left_only"]
        new = new_file.loc[merged[merged["_merge"] == "right_only"]["index_new"]]

        new["is_current"] = True
        new["effective_from"] = date
        new["expiry_date"] = pd.to_datetime("2099-12-31")

        old_file.loc[old["index"], "is_current"] = False
        old_file.loc[old["index"], "expiry_date"] = date

        sys_logger.info(f"Detected {len(old)} old records and {len(new)} new records.")

        return (
            pd.concat([old_file, new], axis=0, ignore_index=True)
            .drop(columns="index", errors="ignore")
            .reset_index(drop=True)
        )

    else:
        if len(old_file) == 0:
            sys_logger.info("No existing records found. Returning new records.")
            new_file["is_current"] = True
            new_file["effective_from"] = date
            new_file["expiry_date"] = pd.to_datetime("2099-12-31")
            return new_file.drop(columns="index", errors="ignore").reset_index(drop=True)
            
        merged = pd.merge(
            old_file[old_file["is_current"]],
            new_file,
            on=key_cols,
            how="outer",
            suffixes=["", "_new"],
            indicator=True,
        )

        changes = merged[
            (merged["_merge"] == "both") & (merged["hash"] != merged["hash_new"])
        ]
        new = merged[merged["_merge"] == "right_only"]

        sys_logger.info(f"Detected {len(changes)} changes and {len(new)} new records.")

        total = pd.concat(
            [new_file.loc[new["index_new"]], new_file.loc[changes["index_new"]]],
            axis=0,
            ignore_index=True,
        ).drop(columns=["index"])

        total["is_current"] = True
        total["effective_from"] = date
        total["expiry_date"] = pd.to_datetime("2099-12-31")
        old_file.loc[changes["index"], "is_current"] = False
        old_file.loc[changes["index"], "expiry_date"] = date

        return (
            pd.concat([old_file, total])
            .drop(columns="index", errors="ignore")
            .reset_index(drop=True)
        )


def process_data(source_name, dataframe, config, date):
    sys_logger.info(f"Processing data for {source_name}")
    key_cols = config.get("key_columns",[])
    is_full = config.get('data_type') == 'full'

    current_table = get_saved_file(source_name)

    schema = config.get('schema')
    clean_records, error_records = validate_data(schema, dataframe)

    sys_logger.warning(f"Found {len(error_records)} error records for {source_name}")
    error_records.to_csv(get_error_filename(source_name, date.strftime('%Y%m%d')), index=False)

    if len(clean_records) > 0:
        new_table = apply_scd2(
            current_table,
            clean_records,
            key_cols,
            date,
            is_full,
        )

        save_file(get_save_filename(source_name), new_table)

    stats = {
        "source": source_name,
        "processed_rows": len(clean_records),
        "error_rows": len(error_records),
        "process_time": pd.Timestamp.now(),
        "file_date": date,
        "file_id": str(uuid4()),
    }

    sys_logger.info(f"Processed {len(clean_records)} records for {source_name}")

    return stats