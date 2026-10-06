import plotly.express as px
import plotly.graph_objects as go


def _template(theme):
    return "plotly_white" if theme == "light" else "plotly_dark"


def _transparent_layout(figure):
    figure.update_layout(
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return figure


def histogram(df, column, theme="dark"):
    if column not in df.columns:
        raise ValueError("Select a valid column for the histogram.")

    figure = px.histogram(
        df,
        x=column,
        nbins=min(max(df[column].nunique(dropna=True), 10), 50),
        template=_template(theme),
        title=f"Histogram of {column}",
    )
    return _transparent_layout(figure)


def scatter(df, x_column, y_column, color_column=None, theme="dark"):
    if x_column not in df.columns or y_column not in df.columns:
        raise ValueError("Select valid x and y columns for the scatter plot.")

    figure = px.scatter(
        df,
        x=x_column,
        y=y_column,
        color=color_column if color_column in df.columns else None,
        template=_template(theme),
        title=f"Scatter Plot: {x_column} vs {y_column}",
        opacity=0.82,
    )
    figure.update_traces(marker={"size": 10, "line": {"width": 0}})
    return _transparent_layout(figure)


def density_heatmap(df, x_column, y_column, theme="dark"):
    if x_column not in df.columns or y_column not in df.columns:
        raise ValueError("Select valid x and y columns for the heatmap.")

    figure = px.density_heatmap(
        df,
        x=x_column,
        y=y_column,
        template=_template(theme),
        title=f"Heatmap: {x_column} vs {y_column}",
        color_continuous_scale="Tealgrn",
    )
    return _transparent_layout(figure)


def correlation_heatmap(df, theme="dark"):
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        raise ValueError("Correlation heatmap requires at least two numeric columns.")

    correlation_matrix = numeric_df.corr(numeric_only=True).round(2)
    figure = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns.tolist(),
            y=correlation_matrix.columns.tolist(),
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            text=correlation_matrix.values,
            texttemplate="%{text}",
            hovertemplate="%{x} vs %{y}: %{z}<extra></extra>",
        )
    )
    figure.update_layout(template=_template(theme), title="Correlation Matrix")
    return _transparent_layout(figure)