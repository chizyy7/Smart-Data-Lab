from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SmartDataLab/2.0"}


def _fetch_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=12)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _push_result(results, seen_urls, source, title, url, description):
    if not url or url in seen_urls:
        return
    seen_urls.add(url)
    results.append(
        {
            "source": source,
            "title": title.strip() or "Untitled dataset",
            "url": url,
            "description": description,
        }
    )


def search_datasets(keyword):
    query = keyword.strip()
    if not query:
        return []

    results = []
    seen_urls = set()

    try:
        kaggle_url = f"https://www.kaggle.com/search?q={quote_plus(query)}"
        soup = _fetch_soup(kaggle_url)
        for anchor in soup.select('a[href*="/datasets/"]'):
            href = anchor.get("href", "")
            title = anchor.get_text(" ", strip=True) or href.rsplit("/", 1)[-1].replace("-", " ")
            _push_result(
                results,
                seen_urls,
                "Kaggle",
                title,
                urljoin("https://www.kaggle.com", href),
                "Dataset result discovered from Kaggle search.",
            )
            if len(results) >= 7:
                break
    except requests.RequestException:
        pass

    try:
        uci_url = "https://archive.ics.uci.edu/ml/datasets.php"
        soup = _fetch_soup(uci_url)
        for anchor in soup.select("a[href]"):
            title = anchor.get_text(" ", strip=True)
            if query.lower() not in title.lower():
                continue
            _push_result(
                results,
                seen_urls,
                "UCI",
                title,
                urljoin("https://archive.ics.uci.edu/ml/", anchor.get("href")),
                "Matched from the UCI Machine Learning Repository.",
            )
            if len(results) >= 11:
                break
    except requests.RequestException:
        pass

    try:
        data_url = f"https://catalog.data.gov/dataset?q={quote_plus(query)}"
        soup = _fetch_soup(data_url)
        for anchor in soup.select('a[href*="/dataset/"]'):
            href = anchor.get("href", "")
            title = anchor.get_text(" ", strip=True)
            _push_result(
                results,
                seen_urls,
                "Data.gov",
                title,
                urljoin("https://catalog.data.gov", href),
                "Open data portal result related to your query.",
            )
            if len(results) >= 15:
                break
    except requests.RequestException:
        pass

    return results[:15]
