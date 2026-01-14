def mock_exchange_rates(base="INR"):
    return {
        "INR": 1,
        "USD": 80,
        "EUR": 90
    }


def test_summary_report_with_mocked_currency(client, monkeypatch):
    # IMPORTANT: clear lru_cache before mocking
    from main import get_exchange_rates
    get_exchange_rates.cache_clear()

    # Mock the external currency API
    monkeypatch.setattr(
        "main.get_exchange_rates",
        mock_exchange_rates
    )

    response = client.get("/report/summary")

    assert response.status_code == 200

    data = response.get_json()
    assert "total_spent" in data
    assert "average_expense" in data
    assert "max_expense" in data

    assert isinstance(data["total_spent"], float)


def test_monthly_report_with_mocked_currency(client, monkeypatch):
    # Clear cache again for safety
    from main import get_exchange_rates
    get_exchange_rates.cache_clear()

    monkeypatch.setattr(
        "main.get_exchange_rates",
        mock_exchange_rates
    )

    response = client.get("/report/monthly")

    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, dict)


def test_pdf_download(client):
    response = client.get("/report/pdf")
    assert response.status_code == 200
    assert response.content_type == "application/pdf"
