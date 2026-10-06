## SmartDataLab 2.0

SmartDataLab is a local AI data science workspace with a Flask backend and a modern HTML, CSS, and JavaScript dashboard.

### Included Features

- Vertical notebook-style interface with stacked cells
- Sidebar with project identity, upload action, theme toggle, and live metrics
- Working dataset upload via file picker, drag-and-drop, and local path input
- CSV, Excel, and JSON loading with pandas through Flask API endpoints
- Automatic notebook outputs after load: `df.head()`, `df.info()`, and `df.describe()`
- Pandas command execution cell with autocomplete suggestions and per-command outputs
- Interactive Plotly visuals: histogram, scatter plot, and correlation heatmap
- AI dataset quality insights panel
- Dataset export buttons for CSV, JSON, and Excel
- Notebook history panel showing executed operations
- Versioned dataset save flow

### Run Locally

1. Install dependencies.

```bash
pip install -r datasets/requirements.txt
```

2. Start the app.

```bash
python app.py
```

3. Open the dashboard at `http://127.0.0.1:5000`.

### Notes

- Saved dataset versions are written into the `datasets` folder.
- The pandas console intentionally supports a curated set of safe commands.
- Kaggle scraping can return fewer results if the public page structure changes or requests are rate-limited.
