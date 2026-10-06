import ast
import io
import re


PANDAS_COMMANDS = [
    'df.head()',
    'df.head(10)',
    'df.tail()',
    'df.info()',
    'df.describe()',
    'df.isnull().sum()',
    'df.dropna()',
    'df.fillna(0)',
    'df.drop_duplicates()',
    'df.value_counts()',
    'df.groupby("column")',
    'df.sort_values("column")',
    'df["column"].value_counts()',
    'df.groupby("column").size()',
    'df.dtypes',
]


def autocomplete(command):
    query = command.strip().lower()
    if not query:
        return PANDAS_COMMANDS[:6]
    return [candidate for candidate in PANDAS_COMMANDS if query in candidate.lower()][:8]


def _column_value_frame(series, value_name):
    frame = series.reset_index()
    frame.columns = ["value", value_name]
    return frame


def execute_command(df, command):
    raw_command = command.strip()
    if not raw_command:
        raise ValueError("Enter a pandas command to run.")

    normalized = raw_command.replace(" ", "")

    if raw_command in {"df.info()", "info()"}:
        buffer = io.StringIO()
        df.info(buf=buffer)
        return {
            "output_type": "text",
            "title": "DataFrame Info",
            "content": buffer.getvalue(),
            "mutated": False,
            "message": "Displayed DataFrame info.",
        }

    if raw_command in {"df.describe()", "describe()"}:
        return {
            "output_type": "table",
            "title": "Descriptive Statistics",
            "data": df.describe(include="all").transpose().reset_index().rename(
                columns={"index": "column"}
            ),
            "mutated": False,
            "message": "Generated descriptive statistics.",
        }

    if raw_command in {"df.isnull().sum()", "isnull().sum()"}:
        return {
            "output_type": "table",
            "title": "Missing Values Summary",
            "data": _column_value_frame(df.isnull().sum(), "missing_values"),
            "mutated": False,
            "message": "Calculated missing values per column.",
        }

    if raw_command in {"df.dtypes", "dtypes"}:
        return {
            "output_type": "table",
            "title": "Column Data Types",
            "data": _column_value_frame(df.dtypes.astype(str), "dtype"),
            "mutated": False,
            "message": "Displayed active column dtypes.",
        }

    head_match = re.fullmatch(r"(?:df\.)?head\((\d+)?\)", raw_command)
    if head_match:
        count = int(head_match.group(1) or 5)
        return {
            "output_type": "table",
            "title": f"Head ({count})",
            "data": df.head(count),
            "mutated": False,
            "message": f"Displayed the first {count} rows.",
        }

    tail_match = re.fullmatch(r"(?:df\.)?tail\((\d+)?\)", raw_command)
    if tail_match:
        count = int(tail_match.group(1) or 5)
        return {
            "output_type": "table",
            "title": f"Tail ({count})",
            "data": df.tail(count),
            "mutated": False,
            "message": f"Displayed the last {count} rows.",
        }

    if raw_command in {"df.dropna()", "dropna()"}:
        cleaned_df = df.dropna().reset_index(drop=True)
        return {
            "output_type": "table",
            "title": "Rows After dropna()",
            "data": cleaned_df.head(10),
            "mutated": True,
            "updated_df": cleaned_df,
            "message": "Applied dropna() to the active dataset.",
        }

    if raw_command in {"df.drop_duplicates()", "drop_duplicates()"}:
        cleaned_df = df.drop_duplicates().reset_index(drop=True)
        return {
            "output_type": "table",
            "title": "Rows After drop_duplicates()",
            "data": cleaned_df.head(10),
            "mutated": True,
            "updated_df": cleaned_df,
            "message": "Applied drop_duplicates() to the active dataset.",
        }

    if raw_command in {"df.value_counts()", "value_counts()"}:
        counts = _column_value_frame(df.value_counts(dropna=False).head(25), "count")
        return {
            "output_type": "table",
            "title": "DataFrame Row Value Counts",
            "data": counts,
            "mutated": False,
            "message": "Calculated value counts for repeated rows.",
        }

    fill_match = re.fullmatch(r"(?:df\.)?fillna\((.+)\)", raw_command)
    if fill_match:
        fill_value = ast.literal_eval(fill_match.group(1))
        cleaned_df = df.fillna(fill_value)
        return {
            "output_type": "table",
            "title": "Rows After fillna()",
            "data": cleaned_df.head(10),
            "mutated": True,
            "updated_df": cleaned_df,
            "message": f"Filled missing values with {fill_value!r}.",
        }

    sort_match = re.fullmatch(
        r"(?:df\.)?sort_values\((['\"])(.+?)\1(?:,ascending=(True|False))?\)",
        normalized,
    )
    if sort_match:
        column = sort_match.group(2)
        ascending = sort_match.group(3) != "False"
        if column not in df.columns:
            raise ValueError(f"Column '{column}' was not found in the dataset.")
        sorted_df = df.sort_values(by=column, ascending=ascending, na_position="last").reset_index(drop=True)
        return {
            "output_type": "table",
            "title": f"Rows After sort_values('{column}')",
            "data": sorted_df.head(10),
            "mutated": True,
            "updated_df": sorted_df,
            "message": f"Sorted the active dataset by {column}.",
        }

    value_counts_match = re.fullmatch(r"df\[(['\"])(.+?)\1\]\.value_counts\(\)", raw_command)
    if value_counts_match:
        column = value_counts_match.group(2)
        if column not in df.columns:
            raise ValueError(f"Column '{column}' was not found in the dataset.")
        counts = _column_value_frame(df[column].value_counts(dropna=False).head(25), "count")
        return {
            "output_type": "table",
            "title": f"Value Counts: {column}",
            "data": counts,
            "mutated": False,
            "message": f"Calculated value counts for {column}.",
        }

    groupby_match = re.fullmatch(r"df\.groupby\((['\"])(.+?)\1\)\.size\(\)", raw_command)
    if groupby_match:
        column = groupby_match.group(2)
        if column not in df.columns:
            raise ValueError(f"Column '{column}' was not found in the dataset.")
        grouped = _column_value_frame(df.groupby(column).size().head(25), "size")
        return {
            "output_type": "table",
            "title": f"Group Counts: {column}",
            "data": grouped,
            "mutated": False,
            "message": f"Grouped the dataset by {column}.",
        }

    groupby_simple_match = re.fullmatch(r"df\.groupby\((['\"])(.+?)\1\)", raw_command)
    if groupby_simple_match:
        column = groupby_simple_match.group(2)
        if column not in df.columns:
            raise ValueError(f"Column '{column}' was not found in the dataset.")
        grouped = _column_value_frame(df.groupby(column).size().head(25), "size")
        return {
            "output_type": "table",
            "title": f"Group Preview: {column}",
            "data": grouped,
            "mutated": False,
            "message": f"Grouped by {column}. Showing group sizes.",
        }

    if raw_command in {"df.groupby()", "groupby()"}:
        return {
            "output_type": "text",
            "title": "GroupBy Usage",
            "content": (
                "Specify a column, for example: df.groupby(\"column\") or "
                "df.groupby(\"column\").size()"
            ),
            "mutated": False,
            "message": "GroupBy needs at least one column.",
        }

    raise ValueError("Unsupported command. Use the autocomplete suggestions for supported pandas operations.")