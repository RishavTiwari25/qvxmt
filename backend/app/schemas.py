"""Pydantic response models. They double as the /docs documentation."""

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str
    data_source: str = Field(description="'cache' (committed snapshot) or 'live' (re-fetched from Elexon)")
    actual_hours: int
    forecast_rows: int
    forecast_vintages: int
    default_cutoff: str


class Summary(BaseModel):
    n: int = Field(description="Matched forecast/actual hours")
    mae: float | None = Field(description="Mean absolute error, MW")
    rmse: float | None = Field(description="Root mean squared error, MW")
    mape: float | None = Field(description="Mean absolute percentage error, % (hours with actual > 0)")
    bias: float | None = Field(description="Mean of forecast - actual, MW (positive = over-forecast)")
    forecast_mwh: float | None
    actual_mwh: float | None


class DaySummary(Summary):
    date: str
    publish_time: str | None = Field(description="Decision-time vintage used, null if none")


class Margin(BaseModel):
    coverage: int = Field(description="Percent of hours in which the margin covers the shortfall")
    margin_mw: float | None


class ForecastPoint(BaseModel):
    time: str
    forecast_mw: float
    actual_mw: float | None
    error_mw: float | None


class VintagePoint(BaseModel):
    time: str
    forecast_mw: float


class Vintage(BaseModel):
    publish_time: str
    before_cutoff: bool
    points: list[VintagePoint]


class ForecastView(BaseModel):
    date: str
    cutoff: str
    cutoff_utc: str
    publish_time: str = Field(description="Decision-time vintage: latest published at or before the cutoff")
    lead_hours_to_day_start: float
    points: list[ForecastPoint]
    summary: Summary
    margins: list[Margin] = Field(description="Month-wide margins at P80/P90/P95")
    vintages: list[Vintage] = Field(description="Every vintage that covers the day, oldest first")


class VintageRow(Summary):
    publish_time: str
    lead_hours_to_day_start: float
    before_cutoff: bool
    hours_covered: int


class HourRow(BaseModel):
    hour: int
    mae: float | None
    bias: float | None
    n: int


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class LeadTimeRow(BaseModel):
    lead_time: str
    mae: float | None
    bias: float | None
    n: int


class Period(BaseModel):
    from_: str = Field(alias="from")
    to: str


class AccuracyReport(BaseModel):
    cutoff: str
    period: Period
    month: Summary
    days: list[DaySummary]
    by_hour: list[HourRow]
    percentiles: dict[str, float | None]
    margins: list[Margin]
    histogram: list[HistogramBin]
    by_lead_time: list[LeadTimeRow]
    over_forecast_share_pct: float | None
