from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WatchConfig:
    event: str
    city: str = ""
    state_code: str = ""
    venue: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_miles: Optional[float] = None
    start_date: str = ""
    end_date: str = ""
    quantity: int = 2
    must_be_together: bool = True
    max_price_each: Optional[float] = None
    max_order_total: Optional[float] = None
    require_fees_included: bool = False
    minimum_event_match: float = 0.55
    check_every_seconds: int = 300
    stop_after_match: bool = True
    open_browser_on_match: bool = True
    sound_alert: bool = True
    browser_headless: bool = False
    browser_offscreen: bool = True
    browser_page_wait_seconds: int = 20

    def validate(self) -> None:
        if not self.event.strip():
            raise ValueError("event cannot be blank")
        if self.quantity < 1:
            raise ValueError("quantity must be at least 1")
        if self.check_every_seconds < 30:
            raise ValueError("check_every_seconds must be at least 30")
        if self.browser_page_wait_seconds < 8:
            raise ValueError("browser_page_wait_seconds must be at least 8")
        if self.browser_headless and self.browser_offscreen:
            raise ValueError("browser_headless and browser_offscreen cannot both be true")
        if not 0 <= self.minimum_event_match <= 1:
            raise ValueError("minimum_event_match must be between 0 and 1")
        location_values = (self.latitude, self.longitude, self.radius_miles)
        if any(value is not None for value in location_values) and not all(value is not None for value in location_values):
            raise ValueError("latitude, longitude, and radius_miles must be supplied together")
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if self.radius_miles is not None and self.radius_miles <= 0:
            raise ValueError("radius_miles must be greater than 0")
        if self.radius_miles is not None and round(self.radius_miles) > 19999:
            raise ValueError("radius_miles must round to 19,999 or less")
        for name, value in (("max_price_each", self.max_price_each), ("max_order_total", self.max_order_total)):
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be greater than 0")


@dataclass(frozen=True)
class Listing:
    source: str
    event_id: str
    event_name: str
    event_url: str
    venue: str
    city: str
    starts_at: Optional[datetime]
    currency: str
    price_each: Optional[float]
    quantity_available: Optional[int] = None
    seats_together: Optional[bool] = None
    fees_included: Optional[bool] = None
    section: str = ""
    row: str = ""
    event_match: float = 0.0
    distance_miles: Optional[float] = None

    @property
    def estimated_total(self) -> Optional[float]:
        return self.price_each


@dataclass(frozen=True)
class Match:
    listing: Listing
    estimated_order_total: Optional[float]
    score: float
    notes: tuple[str, ...]
