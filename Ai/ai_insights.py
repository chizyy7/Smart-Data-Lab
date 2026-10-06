def generate_insight(df):
    insights = []

    rows, columns = df.shape
    total_cells = max(rows * columns, 1)
    missing_by_column = df.isnull().sum().sort_values(ascending=False)
    missing_total = int(missing_by_column.sum())
    duplicate_total = int(df.duplicated().sum())

    if missing_total:
        highest_missing_column = missing_by_column.index[0]
        highest_missing_value = int(missing_by_column.iloc[0])
        insights.append(
            {
                "severity": "warning",
                "title": "Missing values detected",
                "detail": (
                    f"{missing_total} cells are missing across the dataset. "
                    f"{highest_missing_column} has the highest gap with {highest_missing_value} missing values."
                ),
                "recommendation": "Use dropna or fillna before training or reporting.",
            }
        )

    if duplicate_total:
        insights.append(
            {
                "severity": "warning",
                "title": "Duplicate rows found",
                "detail": f"{duplicate_total} duplicate rows can distort aggregates and visual trends.",
                "recommendation": "Remove duplicates before feature engineering or export.",
            }
        )

    constant_columns = [column for column in df.columns if df[column].nunique(dropna=False) <= 1]
    if constant_columns:
        preview_columns = ", ".join(constant_columns[:3])
        insights.append(
            {
                "severity": "info",
                "title": "Low-information columns present",
                "detail": f"{preview_columns} contain one unique value and may not add analytical value.",
                "recommendation": "Review constant columns and drop them if they do not support your use case.",
            }
        )

    object_columns = df.select_dtypes(include="object").columns.tolist()
    suspected_datetime_columns = [
        column
        for column in object_columns
        if any(keyword in column.lower() for keyword in ("date", "time", "day", "month", "year"))
    ]
    if suspected_datetime_columns:
        insights.append(
            {
                "severity": "info",
                "title": "Possible datetime conversion candidates",
                "detail": (
                    "These columns look like time fields but are still stored as text: "
                    f"{', '.join(suspected_datetime_columns[:4])}."
                ),
                "recommendation": "Convert date-like text columns to datetime for trend and seasonality analysis.",
            }
        )

    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] > 1:
        correlations = numeric_df.corr(numeric_only=True).abs()
        for index in range(correlations.shape[0]):
            correlations.iat[index, index] = 0
        highest_correlation = correlations.max().max()
        if highest_correlation >= 0.85:
            pair = correlations.stack().idxmax()
            insights.append(
                {
                    "severity": "info",
                    "title": "High feature correlation found",
                    "detail": (
                        f"{pair[0]} and {pair[1]} are strongly correlated at {highest_correlation:.2f}."
                    ),
                    "recommendation": "Check multicollinearity before regression or feature selection.",
                }
            )

    if not insights:
        insights.append(
            {
                "severity": "success",
                "title": "Dataset quality looks stable",
                "detail": "No major missing-value or duplication issues were detected in the current dataset.",
                "recommendation": "Move into visualization, feature engineering, or modeling.",
            }
        )

    insights.append(
        {
            "severity": "info",
            "title": "Dataset footprint",
            "detail": (
                f"The active workspace contains {rows} rows, {columns} columns, and "
                f"{missing_total} missing cells out of {total_cells} total values."
            ),
            "recommendation": "Use notebook cells to document each cleaning and exploration step.",
        }
    )

    return insights