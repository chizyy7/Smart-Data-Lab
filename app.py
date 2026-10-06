from datetime import datetime
import io
from pathlib import Path
import uuid

from flask import Flask, jsonify, request, send_file
import pandas as pd

from Ai.ai_insights import generate_insight
from code_helper import autocomplete, execute_command
from core.dataset_analyzer import dataset_info, dataset_stats, dataset_summary
from core.dataset_cleaner import apply_cleaning_operation
from core.dataset_loader import load_dataset
from core.dataset_visualizer import correlation_heatmap, density_heatmap, histogram, scatter
from scaping.dataset_scraper import search_datasets
from settings.about_app import app_info
from storage.datasets_history import get_dataset_path, get_dataset_record, list_datasets
from storage.datasets_saver import save_dataset, slugify_name


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 150 * 1024 * 1024
DATASET_STORE = {}


@app.before_request
def handle_api_preflight():
    if request.path.startswith("/api/") and request.method == "OPTIONS":
        return app.make_default_options_response()


@app.after_request
def attach_cors_headers(response):
    if request.path.startswith("/api/"):
        origin = request.headers.get("Origin")
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def _serialize_value(value):
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _serialize_dataframe(df, limit=None):
    working_df = df.head(limit) if limit else df
    columns = [{"name": column, "dtype": str(working_df[column].dtype)} for column in working_df.columns]
    rows = []
    for row in working_df.to_dict(orient="records"):
        rows.append({column: _serialize_value(value) for column, value in row.items()})
    return {"columns": columns, "rows": rows, "row_count": int(len(working_df))}


def _filter_and_sort_preview(df, filter_text="", sort_by=None, sort_dir="asc", limit=50):
    working_df = df.copy()
    if filter_text:
        lowered = filter_text.lower()
        matches = working_df.astype(str).apply(lambda series: series.str.lower().str.contains(lowered, na=False))
        working_df = working_df[matches.any(axis=1)]

    if sort_by in working_df.columns:
        working_df = working_df.sort_values(
            by=sort_by,
            ascending=sort_dir != "desc",
            na_position="last",
        )

    preview = _serialize_dataframe(working_df, limit=limit)
    preview["total_rows"] = int(len(working_df))
    return preview


def _store_dataset(df, name):
    dataset_id = uuid.uuid4().hex[:12]
    DATASET_STORE[dataset_id] = {
        "df": df.copy(),
        "name": name,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return dataset_id


def _get_dataset(dataset_id):
    dataset = DATASET_STORE.get(dataset_id)
    if not dataset:
        raise ValueError("Dataset session was not found. Upload a dataset to continue.")
    return dataset


def _build_dataset_payload(dataset_id, note=None):
    dataset = _get_dataset(dataset_id)
    df = dataset["df"]
    return {
        "datasetId": dataset_id,
        "name": dataset["name"],
        "updatedAt": dataset["updated_at"],
        "summary": dataset_summary(df),
        "preview": _filter_and_sort_preview(df),
        "stats": dataset_stats(df),
        "info": dataset_info(df),
        "insights": generate_insight(df),
        "note": note,
    }


def _error_response(message, status_code=400):
    return jsonify({"error": message}), status_code


def _export_buffer(df, export_format):
    safe_format = export_format.lower()
    if safe_format == "csv":
        content = io.StringIO()
        df.to_csv(content, index=False)
        buffer = io.BytesIO(content.getvalue().encode("utf-8"))
        return buffer, "text/csv", "csv"
    if safe_format == "json":
        content = io.StringIO()
        df.to_json(content, orient="records", indent=2, date_format="iso")
        buffer = io.BytesIO(content.getvalue().encode("utf-8"))
        return buffer, "application/json", "json"
    if safe_format == "xlsx":
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return (
            buffer,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    raise ValueError("Export format must be csv, json, or xlsx.")


def _serialize_command_result(result):
    if result["output_type"] == "text":
        return {
            "type": "text",
            "title": result["title"],
            "content": result["content"],
        }

    serialized = _serialize_dataframe(result["data"], limit=25)
    serialized["type"] = "table"
    serialized["title"] = result["title"]
    return serialized


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ready"})


@app.get("/api/meta")
def meta():
    return jsonify(app_info())


@app.post("/api/upload")
def upload_dataset():
    uploaded_file = request.files.get("dataset")
    if not uploaded_file or not uploaded_file.filename:
        return _error_response("Select a CSV, Excel, or JSON file to continue.")

    try:
        dataframe = load_dataset(uploaded_file, uploaded_file.filename)
    except Exception as exc:
        return _error_response(f"Unable to load dataset: {exc}")

    dataset_id = _store_dataset(dataframe, Path(uploaded_file.filename).stem)
    payload = _build_dataset_payload(dataset_id, note=f"Loaded {uploaded_file.filename} into the active workspace.")
    return jsonify(payload)


@app.post("/api/upload-path")
def upload_dataset_from_path():
    payload = request.get_json(silent=True) or {}
    raw_path = (payload.get("path") or "").strip()
    if not raw_path:
        return _error_response("Enter a valid local dataset path.")

    dataset_path = Path(raw_path).expanduser()
    if not dataset_path.exists() or not dataset_path.is_file():
        return _error_response("Dataset path does not exist or is not a file.")

    try:
        dataframe = load_dataset(str(dataset_path), dataset_path.name)
    except Exception as exc:
        return _error_response(f"Unable to load dataset from path: {exc}")

    dataset_id = _store_dataset(dataframe, dataset_path.stem)
    response = _build_dataset_payload(
        dataset_id,
        note=f"Loaded dataset from local path {dataset_path}.",
    )
    response["sourcePath"] = str(dataset_path)
    return jsonify(response)


@app.get("/api/preview/<dataset_id>")
def preview_dataset(dataset_id):
    try:
        dataset = _get_dataset(dataset_id)
    except ValueError as exc:
        return _error_response(str(exc), 404)

    preview = _filter_and_sort_preview(
        dataset["df"],
        filter_text=request.args.get("filter", ""),
        sort_by=request.args.get("sortBy"),
        sort_dir=request.args.get("sortDir", "asc"),
        limit=max(10, min(int(request.args.get("limit", 50)), 150)),
    )
    return jsonify(preview)


@app.post("/api/clean/<dataset_id>")
def clean_dataset(dataset_id):
    try:
        dataset = _get_dataset(dataset_id)
    except ValueError as exc:
        return _error_response(str(exc), 404)

    payload = request.get_json(silent=True) or {}
    operation = payload.get("operation")
    try:
        cleaned_df, message = apply_cleaning_operation(
            dataset["df"],
            operation,
            value=payload.get("value"),
            column=payload.get("column"),
            dtype=payload.get("dtype"),
        )
    except Exception as exc:
        return _error_response(str(exc))

    dataset["df"] = cleaned_df
    dataset["updated_at"] = datetime.now().isoformat(timespec="seconds")
    response = _build_dataset_payload(dataset_id, note=message)
    response["operation"] = {"name": operation, "message": message}
    return jsonify(response)


@app.get("/api/console/suggestions")
def console_suggestions():
    query = request.args.get("query", "")
    return jsonify({"suggestions": autocomplete(query)})


@app.post("/api/console/<dataset_id>")
def run_console_command(dataset_id):
    try:
        dataset = _get_dataset(dataset_id)
    except ValueError as exc:
        return _error_response(str(exc), 404)

    payload = request.get_json(silent=True) or {}
    command = payload.get("command", "")
    try:
        result = execute_command(dataset["df"], command)
    except Exception as exc:
        return jsonify({"error": str(exc), "suggestions": autocomplete(command)}), 400

    if result.get("mutated"):
        dataset["df"] = result["updated_df"]
        dataset["updated_at"] = datetime.now().isoformat(timespec="seconds")

    response = {
        "command": command,
        "message": result["message"],
        "result": _serialize_command_result(result),
        "dataset": _build_dataset_payload(dataset_id, note=result["message"]),
        "suggestions": autocomplete(command),
    }
    return jsonify(response)


@app.post("/api/chart/<dataset_id>")
def create_chart(dataset_id):
    try:
        dataset = _get_dataset(dataset_id)
    except ValueError as exc:
        return _error_response(str(exc), 404)

    payload = request.get_json(silent=True) or {}
    chart_type = payload.get("type")
    theme = payload.get("theme", "dark")
    df = dataset["df"]

    try:
        if chart_type == "histogram":
            figure = histogram(df, payload.get("x"), theme)
        elif chart_type == "scatter":
            figure = scatter(df, payload.get("x"), payload.get("y"), payload.get("color"), theme)
        elif chart_type == "heatmap":
            figure = density_heatmap(df, payload.get("x"), payload.get("y"), theme)
        elif chart_type == "correlation":
            figure = correlation_heatmap(df, theme)
        else:
            return _error_response("Select a supported chart type.")
    except Exception as exc:
        return _error_response(str(exc))

    return jsonify({"figure": figure.to_plotly_json(), "chartType": chart_type})


@app.get("/api/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"query": "", "results": []})

    results = search_datasets(query)
    return jsonify({"query": query, "results": results})


@app.post("/api/save/<dataset_id>")
def save_active_dataset(dataset_id):
    try:
        dataset = _get_dataset(dataset_id)
    except ValueError as exc:
        return _error_response(str(exc), 404)

    payload = request.get_json(silent=True) or {}
    name = payload.get("name") or dataset["name"]
    file_format = payload.get("format", "csv")
    try:
        record = save_dataset(dataset["df"], name, file_format)
    except Exception as exc:
        return _error_response(str(exc))

    return jsonify(
        {
            "message": f"Saved dataset version as {record['file_name']}.",
            "record": record,
            "history": list_datasets(),
        }
    )


@app.post("/api/export/<dataset_id>")
def export_active_dataset(dataset_id):
    try:
        dataset = _get_dataset(dataset_id)
    except ValueError as exc:
        return _error_response(str(exc), 404)

    payload = request.get_json(silent=True) or {}
    export_format = payload.get("format", "csv")
    file_name = payload.get("name") or dataset["name"]
    try:
        buffer, mimetype, extension = _export_buffer(dataset["df"], export_format)
    except Exception as exc:
        return _error_response(str(exc))

    safe_name = slugify_name(file_name)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"{safe_name}.{extension}",
    )


@app.get("/api/history")
def dataset_history():
    return jsonify({"history": list_datasets()})


@app.post("/api/history/load")
def load_history_version():
    payload = request.get_json(silent=True) or {}
    dataset_id = payload.get("datasetId")
    if not dataset_id:
        return _error_response("Select a saved dataset version to restore.")

    record = get_dataset_record(dataset_id)
    file_path = get_dataset_path(dataset_id)
    if not file_path:
        return _error_response("Saved dataset version could not be found.", 404)

    try:
        dataframe = load_dataset(file_path, file_path.name)
    except Exception as exc:
        return _error_response(f"Unable to load saved dataset: {exc}")

    workspace_name = record.get("display_name") if record else file_path.stem
    workspace_dataset_id = _store_dataset(dataframe, workspace_name)
    payload = _build_dataset_payload(
        workspace_dataset_id,
        note=f"Restored saved version {file_path.name} into the active workspace.",
    )
    payload["historySource"] = dataset_id
    return jsonify(payload)


if __name__ == "__main__":
    app.run(debug=True)