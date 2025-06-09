"""File handler module for managing file operations in the scraper project.
This module provides various utility functions for handling files, including:
- Path construction for downloads
- File discovery
- Column name sanitization
- Blob storage path construction
- CSV file manipulation
- CSV to Parquet conversion
- Directory traversal
"""

import logging
import os
import re

from datetime import datetime, timezone
from typing import Iterable

from ..utils.constant import (
    BASE_DIRECTORY,
    DOWNLOAD,
    ETL_LOADED_TIMESTAMP_COL,
    PROJECT_NAME,
)

logger = logging.getLogger(__name__)
# pylint: disable=import-outside-toplevel


def get_download_location(
    run_id: str, scraper_id: str, suffix=DOWNLOAD, execution_date=None
) -> str:
    """
    Constructs and returns the download location path based on the provided parameters.
    Args:
        run_id (str): A unique identifier for the run.
        scraper_id (str): A unique identifier for the scraper.
        suffix (str, optional): An additional suffix to append to the path. Defaults to DOWNLOAD.
        execution_date (str, optional): The execution date in "YYYY-MM-DD" format.
            If not provided, the current UTC date is used.
    Returns:
        str: The constructed file path for the download location.
    """
    if not execution_date:
        execution_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    run_id = str(run_id)
    scraper_id = str(scraper_id)

    if not suffix:
        return os.path.join(BASE_DIRECTORY, scraper_id, execution_date, run_id)

    return os.path.join(BASE_DIRECTORY, scraper_id, execution_date, run_id, suffix)


def get_all_file_inside_path(folder_path: str) -> list[str]:
    """
    Retrieves all files inside the specified folder path. If the provided path
    is a file, it returns a list containing only that file.

    Args:
        folder_path (str): The path to the folder or file.

    Returns:
        list[str]: A list of full file paths. If the input is a file, the list
        contains only that file's path. If the input is a folder, the list
        contains the full paths of all files in the folder.
    """
    if os.path.isfile(folder_path):
        return [folder_path]

    files = next(os.walk(folder_path), (None, None, []))[2]
    full_paths = [os.path.join(folder_path, file) for file in files]
    return full_paths


def rename_column(columns: Iterable[str], pattern=r"[^a-zA-Z0-9]"):
    """
    Renames a list of column names by replacing characters that do not match the specified pattern
    with underscores and prepends a prefix to column names that start with a number.

    Args:
        columns (Iterable[str]): An iterable of column names to be renamed.
        pattern (str, optional): A regular expression pattern to match characters that should
            be replaced. Defaults to r"[^a-zA-Z0-9]", which matches any character that is not
            alphanumeric.

    Returns:
        List[str]: A list of renamed column names where:
            - Non-alphanumeric characters are replaced with underscores.
            - Column names starting with a number are prefixed with "B_".
    """
    start_with_number = r"^[0-9]+.*"
    new_columns = []
    for column in columns:
        column = re.sub(pattern, "_", column)
        if re.match(start_with_number, column):
            column = f"B_{column}"
        new_columns.append(column)
    return new_columns


def get_blob_path(
    file_path: str,
    suffix: str,
    scraper_id: str,
    execution_date: str,
    run_id: str,
    parent_dir=PROJECT_NAME,
):
    """
    Constructs a blob storage path for a given file.

    Args:
        file_path (str): The full path of the file to be stored.
        suffix (str): A suffix to append to the blob path, typically indicating a subdirectory or file type.
        scraper_id (str): The unique identifier for the scraper.
        execution_date (str): The execution date of the scraper in string format.
        run_id (str): The unique identifier for the specific run of the scraper.
        parent_dir (str, optional): The root directory for the blob path. Defaults to the value of PROJECT_NAME.

    Returns:
        str: The constructed blob storage path.
    """
    file_name = os.path.basename(file_path)
    blob_path = os.path.join(
        parent_dir, scraper_id, execution_date, str(run_id), suffix, file_name
    )
    return blob_path


def remove_last_rows(csv_path, last_row=0):
    """
    Removes the specified number of rows from the end of a CSV file and writes the
    remaining rows to a new file.

    Args:
        csv_path (str): The file path to the original CSV file.
        last_row (int, optional): The number of rows to remove from the end of the file.
                                  Defaults to 0, which means no rows are removed.

    Returns:
        str: The file path to the new CSV file with the specified rows removed.

    Notes:
        - If `last_row` is greater than the total number of rows in the file, all rows
          will be removed, and a warning will be logged.
        - The new file will have the same name as the original file with `.moved__.csv`
          appended to it.

    Raises:
        FileNotFoundError: If the specified `csv_path` does not exist.
        IOError: If there is an issue reading from or writing to the file.
    """
    if not last_row:
        return csv_path
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    row_count = len(lines)
    if row_count < last_row:
        logger.warning(
            "File only have %s row(s) but you skipped  %s", row_count, last_row
        )
        last_row = row_count

    new_path = f"{csv_path}.moved__.csv"
    with open(new_path, "w", encoding="utf-8") as f:
        f.writelines(lines[: -1 * last_row])

    return new_path


def is_column_exists(csv_path: str, column_name="arn", skip_header=0):
    """
    Checks if a specified column exists in a CSV file.

    Args:
        csv_path (str): The file path to the CSV file.
        column_name (str, optional): The name of the column to check for. Defaults to "arn".
        skip_header (int, optional): The number of rows to skip at the start of the file. Defaults to 0.

    Returns:
        bool: True if the column exists in the CSV file, False otherwise.
    """
    import pyarrow.csv as pv

    if not csv_path or not os.path.exists(csv_path) or not column_name:
        return False
    read_options = pv.ReadOptions(skip_rows=skip_header)
    table = pv.read_csv(csv_path, read_options=read_options)
    return column_name in table.schema.names


def convert_csv_to_parquet(
    run_id: str,
    csv_path: str,
    rename_pattern=r"[^a-zA-Z0-9]",
    skip_header=0,
    skip_footer=0,
    arn_column_name=None,
):
    """
    Converts a CSV file to a Parquet file with additional metadata columns.

    Args:
        run_id (str): A unique identifier for the current run, added as a column to the output.
        csv_path (str): The file path of the input CSV file.
        rename_pattern (str, optional): A regex pattern to rename column names. Defaults to r"[^a-zA-Z0-9]".
        skip_header (int, optional): Number of rows to skip at the beginning of the CSV file. Defaults to 0.
        skip_footer (int, optional): Number of rows to skip at the end of the CSV file. Defaults to 0.
        arn_column_name (str, optional): Name of a specific column to enforce as a string type. Defaults to None.

    Returns:
        str: The file path of the generated Parquet file.

    Raises:
        ValueError: If the input CSV file does not exist or is invalid.
        Exception: For any errors encountered during the conversion process.

    Notes:
        - Adds two additional columns to the Parquet file:
            1. `B__run_id`: Contains the `run_id` value for all rows.
            2. `B__converted_date`: Contains the UTC timestamp of the conversion.
        - If `rename_pattern` is provided, column names are sanitized based on the pattern.
        - If `skip_footer` is greater than 0, the specified number of rows are removed from the end of the CSV file.
    """
    import pyarrow as pa
    import pyarrow.csv as pv
    import pyarrow.parquet as pq

    run_id_col_name = "B__run_id"
    converted_date_col_name = "B__converted_date"
    org_csv_path = csv_path
    if skip_footer:
        csv_path = remove_last_rows(csv_path=csv_path, last_row=skip_footer)

    read_options = pv.ReadOptions(skip_rows=skip_header)
    if is_column_exists(
        csv_path=csv_path, column_name=arn_column_name, skip_header=skip_header
    ):
        column_types = {arn_column_name: pa.string()}
        read_options = pv.ReadOptions(skip_rows=skip_header, column_types=column_types)

    table = pv.read_csv(csv_path, read_options=read_options)

    num_rows = table.num_rows

    parquet_path = org_csv_path.replace(".csv", ".parquet")

    run_id_col = pa.array([str(run_id)] * num_rows, type=pa.string())
    converted_date_col = pa.array(
        [datetime.now(timezone.utc)] * num_rows, type=pa.timestamp("s", tz="UTC")
    )

    if run_id_col_name in table.column_names:
        table.drop(run_id_col_name)
    if converted_date_col_name in table.column_names:
        table.drop(converted_date_col_name)

    table = table.append_column(run_id_col_name, run_id_col)
    table = table.append_column(converted_date_col_name, converted_date_col)

    if rename_pattern:
        columns = table.schema.names
        renamed_columns = rename_column(columns, pattern=rename_pattern)
        table = table.rename_columns(renamed_columns)

    pq.write_table(table, parquet_path)

    return parquet_path


def get_columns_in_parquets(parquet_path: str):
    """
    Retrieves the set of column names from a Parquet file and adds a predefined
    timestamp column to the set.

    Args:
        parquet_path (str): The file path to the Parquet file.

    Returns:
        set: A set containing the column names from the Parquet file, including
        the additional ETL timestamp column.
    """
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path)
    columns = set(table.column_names)
    columns.add(ETL_LOADED_TIMESTAMP_COL)
    return columns


def get_parent_folder(path, levels_up=0):
    """
    Retrieves the parent folder of a given file or directory path.

    Args:
        path (str): The file or directory path for which the parent folder is to be determined.
        levels_up (int, optional): The number of levels to traverse up the directory hierarchy.
                                   Defaults to 0, which returns the immediate parent folder.

    Returns:
        str: The path to the parent folder after traversing the specified number of levels up.
    """
    path = os.path.dirname(path)
    while levels_up > 0:
        levels_up = levels_up - 1
        path = os.path.dirname(path)
    return path
