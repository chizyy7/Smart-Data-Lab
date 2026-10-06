import io

import pandas as pd


def dataset_info(df):
    buffer = io.StringIO()
    df.info(buf=buffer)
    return buffer.getvalue()


def dataset_stats(df):
    if df.empty:
        return []

    stats = df.describe(include="all").transpose().reset_index()
    stats = stats.rename(columns={"index": "column"})
    stats = stats.where(pd.notnull(stats), None)
    return stats.to_dict(orient="records")


def missing_values(df):
    total_rows = max(len(df), 1)
    summary = []
    for column, value in df.isnull().sum().sort_values(ascending=False).items():
        if int(value) <= 0:
            continue
        summary.append(
            {
                "column": column,
                "missing": int(value),
                "percentage": round((int(value) / total_rows) * 100, 2),
            }
        )
    return summary


def dataset_summary(df):
    rows, columns = df.shape
    missing_total = int(df.isnull().sum().sum())
    duplicate_total = int(df.duplicated().sum())
    total_cells = max(rows * columns, 1)
    quality_penalty = (missing_total / total_cells) * 100
    if rows:
        quality_penalty += (duplicate_total / rows) * 25
    quality_score = max(0, min(100, round(100 - quality_penalty, 1)))

    return {
        "rows": int(rows),
        "columns": int(columns),
        "missing_total": missing_total,
        "duplicate_total": duplicate_total,
        "quality_score": quality_score,
        "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
        "categorical_columns": df.select_dtypes(exclude="number").columns.tolist(),
        "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "column_names": df.columns.tolist(),
    }


def preview_records(df, limit=50):
    preview = df.head(limit).copy()
    preview = preview.where(pd.notnull(preview), None)
    return preview.to_dict(orient="records")