from pathlib import Path
from time import perf_counter

from connected_health.providers.apple.config import AppleProviderConfig
from connected_health.providers.apple.errors import (
    AppleHealthError,
    ExportXmlNotFoundError,
    ExportXmlTooLargeError,
    HealthDataParseError,
    InvalidArchiveError,
    MultipleExportXmlError,
)
from connected_health.providers.apple.importer import AppleHealthImporter
from connected_health.providers.apple.parser import AppleHealthParser
from connected_health.providers.contract import (
    DatasetProvenance,
    HealthDataProviderError,
    LoadedHealthData,
    ProviderLoadDiagnostics,
)


class AppleHealthProvider:
    """Apple ZIP/XML adapter that emits canonical health data."""

    provider_id = "apple_health"
    _DISPLAY_LABEL = "Apple Health"

    def load(
        self,
        path: Path,
        *,
        config: object,
        report_timezone: str | None = None,
    ) -> LoadedHealthData:
        if not isinstance(config, AppleProviderConfig):
            raise TypeError("AppleHealthProvider requires AppleProviderConfig.")

        archive_open_started = perf_counter()
        try:
            with AppleHealthImporter(path).open_export() as xml_stream:
                archive_open_seconds = perf_counter() - archive_open_started
                parse_started = perf_counter()
                parser_arguments = {"config": config}
                if report_timezone is not None:
                    parser_arguments["report_timezone"] = report_timezone
                data = AppleHealthParser(xml_stream, **parser_arguments).parse()
                parse_seconds = perf_counter() - parse_started
        except AppleHealthError as exc:
            raise HealthDataProviderError(self._error_category(exc)) from exc

        return LoadedHealthData(
            data=data,
            provenance=DatasetProvenance(
                provider_id=self.provider_id,
                display_label=self._DISPLAY_LABEL,
            ),
            diagnostics=ProviderLoadDiagnostics(
                archive_open_seconds=archive_open_seconds,
                parse_seconds=parse_seconds,
            ),
        )

    @staticmethod
    def _error_category(error: AppleHealthError) -> str:
        if isinstance(error, InvalidArchiveError):
            return "invalid_archive"
        if isinstance(error, ExportXmlTooLargeError):
            return "input_too_large"
        if isinstance(error, ExportXmlNotFoundError):
            return "missing_export_xml"
        if isinstance(error, MultipleExportXmlError):
            return "multiple_export_xml"
        if isinstance(error, HealthDataParseError):
            return "malformed_data"
        return "invalid_input"
