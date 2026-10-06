from pathlib import Path
import json

import pandas as pd


SUPPORTED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}


def _resolve_extension(filename):
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Supported types: {supported}.")
    return extension


def _read_json(source):
    if isinstance(source, (str, Path)):
        return pd.read_json(source)

    raw_content = source.read() if hasattr(source, "read") else source
    if hasattr(source, "seek"):
        source.seek(0)

    if isinstance(raw_content, bytes):
        raw_content = raw_content.decode("utf-8")

    payload = json.loads(raw_content)
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            return pd.DataFrame(payload["data"])
        if any(isinstance(value, list) for value in payload.values()):
            return pd.DataFrame(payload)
        return pd.json_normalize(payload)

    raise ValueError("JSON dataset structure is not supported.")


def load_dataset(file_source, filename=None):
    inferred_name = (
        filename
        or getattr(file_source, "filename", None)
        or getattr(file_source, "name", None)
    )
    if not inferred_name:
        raise ValueError("A filename is required to load the dataset.")

    extension = _resolve_extension(inferred_name)
    stream = getattr(file_source, "stream", file_source)

    if extension == "csv":
        return pd.read_csv(stream)
    if extension in {"xlsx", "xls"}:
        return pd.read_excel(stream)
    return _read_json(stream)