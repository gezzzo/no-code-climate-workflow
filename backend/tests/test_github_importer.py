from app.services.github_importer import resolve_github_file_url


def test_resolve_github_blob_url_to_raw_url():
    resolved = resolve_github_file_url(
        "https://github.com/example/climate-data/blob/main/samples/weather.csv"
    )

    assert resolved.download_url == (
        "https://raw.githubusercontent.com/example/climate-data/main/samples/weather.csv"
    )
    assert resolved.filename == "weather.csv"
    assert resolved.repository == "example/climate-data"
    assert resolved.ref == "main"
    assert resolved.path == "samples/weather.csv"


def test_resolve_raw_github_url():
    resolved = resolve_github_file_url(
        "https://raw.githubusercontent.com/example/climate-data/main/samples/weather.csv"
    )

    assert resolved.download_url == (
        "https://raw.githubusercontent.com/example/climate-data/main/samples/weather.csv"
    )
    assert resolved.filename == "weather.csv"
    assert resolved.repository == "example/climate-data"
