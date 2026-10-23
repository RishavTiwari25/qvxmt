"""Endpoint tests against the synthetic dataset (see conftest.py)."""

import pytest


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["data_source"] == "test"
    assert body["actual_hours"] == 48
    assert body["forecast_vintages"] == 5


def test_days_lists_all_of_january(client):
    days = client.get("/api/days").json()
    assert len(days) == 31
    by_date = {d["date"]: d for d in days}
    # 10 Jan: decision vintage 11,500 vs actual 10,000 -> error +1,500 every hour.
    assert by_date["2026-01-10"]["publish_time"] == "2026-01-09T07:30:00+00:00"
    assert by_date["2026-01-10"]["mae"] == 1500
    assert by_date["2026-01-10"]["bias"] == 1500
    assert by_date["2026-01-10"]["mape"] == 15
    # 11 Jan: partial vintage, only 6 matched hours.
    assert by_date["2026-01-11"]["n"] == 6
    # 12 Jan: a vintage exists but no actuals -> n == 0, metrics null.
    assert by_date["2026-01-12"]["publish_time"] is not None
    assert by_date["2026-01-12"]["n"] == 0 and by_date["2026-01-12"]["mae"] is None
    # Days with no vintage at all.
    assert by_date["2026-01-20"]["publish_time"] is None


def test_forecast_default_cutoff(client):
    body = client.get("/api/forecast", params={"date": "2026-01-10"}).json()
    assert body["publish_time"] == "2026-01-09T07:30:00+00:00"
    assert body["cutoff"] == "09:00"
    assert body["lead_hours_to_day_start"] == 16.5
    assert len(body["points"]) == 24
    assert body["points"][0] == {
        "time": "2026-01-10T00:00:00+00:00",
        "forecast_mw": 11500.0,
        "actual_mw": 10000.0,
        "error_mw": 1500.0,
    }
    assert body["summary"]["forecast_mwh"] == 11500 * 24
    assert [v["before_cutoff"] for v in body["vintages"]] == [True, True, False]
    assert {m["coverage"] for m in body["margins"]} == {80, 90, 95}


def test_forecast_custom_cutoff_changes_vintage(client):
    body = client.get("/api/forecast", params={"date": "2026-01-10", "cutoff": "12:00"}).json()
    assert body["publish_time"] == "2026-01-09T11:30:00+00:00"
    assert body["points"][0]["forecast_mw"] == 10200.0


def test_forecast_404_when_nothing_published_before_cutoff(client):
    r = client.get("/api/forecast", params={"date": "2026-01-10", "cutoff": "01:00"})
    assert r.status_code == 404


@pytest.mark.parametrize("params", [{"date": "2026-02-01"}, {"date": "2025-12-31"}])
def test_forecast_404_outside_january(client, params):
    assert client.get("/api/forecast", params=params).status_code == 404


@pytest.mark.parametrize("params", [{"date": "15-01-2026"}, {"cutoff": "9am"}, {"cutoff": "24:00"}])
def test_forecast_422_on_malformed_input(client, params):
    assert client.get("/api/forecast", params=params).status_code == 422


def test_vintages_evolution(client):
    rows = client.get("/api/vintages", params={"date": "2026-01-10"}).json()
    assert [r["publish_time"] for r in rows] == [
        "2026-01-09T02:30:00+00:00",
        "2026-01-09T07:30:00+00:00",
        "2026-01-09T11:30:00+00:00",
    ]
    assert [r["bias"] for r in rows] == [2000, 1500, 200]
    assert rows[0]["lead_hours_to_day_start"] == 21.5


def test_vintages_404_for_uncovered_day(client):
    assert client.get("/api/vintages", params={"date": "2026-01-25"}).status_code == 404


def test_accuracy_report_shape(client):
    body = client.get("/api/accuracy").json()
    assert body["period"] == {"from": "2026-01-01", "to": "2026-01-31"}
    assert body["month"]["n"] == 30  # 24 hours (10 Jan) + 6 hours (11 Jan)
    assert body["month"]["bias"] == pytest.approx((1500 * 24 + 1000 * 6) / 30, abs=0.1)
    assert len(body["days"]) == 31
    assert len(body["by_hour"]) == 24
    assert body["percentiles"]["p50"] == 1500
    assert {m["coverage"] for m in body["margins"]} == {50, 80, 90, 95, 99}
    assert sum(b["count"] for b in body["histogram"]) == 30
    assert body["over_forecast_share_pct"] == 100
    assert body["by_lead_time"]  # non-empty


def test_openapi_docs_are_served(client):
    assert client.get("/api/openapi.json").status_code == 200
