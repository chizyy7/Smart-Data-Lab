import pandas as pd


def remove_missing(df):
    return df.dropna().reset_index(drop=True)


def remove_duplicates(df):
    return df.drop_duplicates().reset_index(drop=True)


def fill_missing(df, value):
    return df.fillna(value)


def convert_datatype(df, column, target_type):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' was not found in the dataset.")

    updated_df = df.copy()
    if target_type == "datetime":
        updated_df[column] = pd.to_datetime(updated_df[column], errors="coerce")
    elif target_type == "string":
        updated_df[column] = updated_df[column].astype("string")
    elif target_type == "category":
        updated_df[column] = updated_df[column].astype("category")
    elif target_type == "boolean":
        updated_df[column] = updated_df[column].astype("boolean")
    elif target_type in {"int64", "float64"}:
        updated_df[column] = pd.to_numeric(updated_df[column], errors="coerce")
        if target_type == "int64":
            updated_df[column] = updated_df[column].astype("Int64")
    else:
        updated_df[column] = updated_df[column].astype(target_type)

    return updated_df


def apply_cleaning_operation(df, operation, **kwargs):
    if operation == "dropna":
        return remove_missing(df), "Dropped rows containing missing values."
    if operation == "fillna":
        fill_value = kwargs.get("value", "")
        return fill_missing(df, fill_value), f"Filled missing values with {fill_value!r}."
    if operation == "remove_duplicates":
        return remove_duplicates(df), "Removed duplicate rows from the active dataset."
    if operation == "convert_dtype":
        column = kwargs.get("column")
        target_type = kwargs.get("dtype")
        if not column or not target_type:
            raise ValueError("Both column and dtype are required for datatype conversion.")
        return convert_datatype(df, column, target_type), f"Converted {column} to {target_type}."

    raise ValueError("Unsupported cleaning operation.")