from pathlib import Path

import pytest

from src.canonical.model import (
    CanonicalDocument,
    CanonicalPage,
    DocumentFormat,
)
from src.ingest.base import (
    FormatAdapter,
    UnsupportedFormatError,
)
from src.ingest.resolver import (
    LocalPIDResolver,
    build_local_resolver,
)
from src.ingest.service import IngestionService
from src.ingest.source import DocumentSource

from src.ingest.resolver import (
    LocalDocumentConfig,
    LocalPIDResolver,
    build_local_resolver,
)

class FakePDFAdapter(FormatAdapter):
    

    @property
    def document_format(self) -> DocumentFormat:
        return DocumentFormat.NATIVE_PDF

    def supports(self, source: DocumentSource) -> bool:
        return source.extension == ".pdf"

    def ingest(
        self,
        source: DocumentSource,
    ) -> CanonicalDocument:
        return CanonicalDocument(
            pid=source.pid,
            revision=source.revision,
            source_format=self.document_format,
            filename=source.filename,
            pages=[
                CanonicalPage(
                    page_number=1,
                    width=612,
                    height=792,
                )
            ],
        )


def test_document_source_reads_bytes(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.pdf"
    file_path.write_bytes(b"sample document")

    source = DocumentSource(
        pid="PID-A",
        file_path=file_path,
    )

    assert source.extension == ".pdf"
    assert source.read_bytes() == b"sample document"


def test_local_resolver_resolves_known_pid(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "revision-a.pdf"
    file_path.write_bytes(b"pdf data")

    resolver = LocalPIDResolver(
        {
            "PID-A": DocumentSource(
                pid="PID-A",
                file_path=file_path,
                revision="A",
            )
        }
    )

    source = resolver.resolve("PID-A")

    assert source.pid == "PID-A"
    assert source.revision == "A"
    assert source.file_path == file_path


def test_local_resolver_rejects_unknown_pid(
    tmp_path: Path,
) -> None:
    resolver = LocalPIDResolver({})

    with pytest.raises(KeyError, match="Unknown PID"):
        resolver.resolve("PID-MISSING")


def test_build_local_resolver(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "document.pdf"
    file_path.write_bytes(b"pdf")

    resolver = build_local_resolver(
        {
            "PID-A": file_path,
        }
    )

    source = resolver.resolve("PID-A")

    assert source.filename == "document.pdf"


def test_ingestion_service_selects_supported_adapter(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "revision-a.pdf"
    file_path.write_bytes(b"pdf data")

    resolver = build_local_resolver(
        {
            "PID-A": file_path,
        }
    )

    service = IngestionService(
        resolver=resolver,
        adapters=[FakePDFAdapter()],
    )

    document = service.ingest("PID-A")

    assert document.pid == "PID-A"
    assert document.source_format == DocumentFormat.NATIVE_PDF
    assert document.page_count == 1


def test_ingestion_service_rejects_unsupported_format(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "drawing.dwg"
    file_path.write_bytes(b"dwg data")

    resolver = build_local_resolver(
        {
            "PID-DWG": file_path,
        }
    )

    service = IngestionService(
        resolver=resolver,
        adapters=[FakePDFAdapter()],
    )

    with pytest.raises(
        UnsupportedFormatError,
        match="No adapter supports",
    ):
        service.ingest("PID-DWG")


def test_ingestion_service_requires_adapter(
    tmp_path: Path,
) -> None:
    resolver = build_local_resolver({})

    with pytest.raises(
        ValueError,
        match="At least one format adapter",
    ):
        IngestionService(
            resolver=resolver,
            adapters=[],
        )

def test_build_local_resolver_with_revision_metadata(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "revision-b.pdf"
    file_path.write_bytes(b"pdf")

    resolver = build_local_resolver(
        {
            "PID-B": LocalDocumentConfig(
                file_path=file_path,
                revision="B",
                metadata={
                    "project": "Pump Upgrade",
                },
            ),
        }
    )

    source = resolver.resolve("PID-B")

    assert source.revision == "B"
    assert source.metadata["project"] == "Pump Upgrade"