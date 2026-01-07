"""JSON export formatter implementation."""

import json
from datetime import datetime
from decimal import Decimal

from src.reports.models.export_models import ReportJsonExport


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class JsonExportFormatter:
    """
    Formats export data as JSON.

    Single Responsibility: Only handles JSON serialization.
    """

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        self._indent = indent
        self._ensure_ascii = ensure_ascii

    def format(self, export_data: ReportJsonExport) -> bytes:
        """Format export data as JSON bytes."""
        json_str = json.dumps(
            export_data.model_dump(mode="json"),
            indent=self._indent,
            ensure_ascii=self._ensure_ascii,
            cls=DecimalEncoder,
        )
        return json_str.encode("utf-8")

    @property
    def content_type(self) -> str:
        return "application/json"

    @property
    def file_extension(self) -> str:
        return "json"
