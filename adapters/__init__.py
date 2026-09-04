"""Module adapters for the Universal Watcher control plane."""

from .family_deals import FamilyDealsAdapter, normalize_family_deals_job
from .tickets import TicketWatcherAdapter, normalize_ticket_job

__all__ = [
    "FamilyDealsAdapter",
    "TicketWatcherAdapter",
    "normalize_family_deals_job",
    "normalize_ticket_job",
]
