from __future__ import annotations

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)

from src.canonical.docling_mapper import (
    DoclingCanonicalMapper,
)
from src.canonical.model import (
    CanonicalDocument,
    DocumentFormat,
)
from src.ingest.base import FormatAdapter
from src.ingest.source import DocumentSource


class DoclingPDFAdapter(FormatAdapter):
    

    def __init__(
        self,
        *,
        enable_ocr: bool = True,
        enable_tables: bool = False,
        max_num_pages: int = 100,
        max_file_size_mb: int = 50,
        mapper: DoclingCanonicalMapper | None = None,
    ) -> None:
        if max_num_pages <= 0:
            raise ValueError(
                "max_num_pages must be positive"
            )

        if max_file_size_mb <= 0:
            raise ValueError(
                "max_file_size_mb must be positive"
            )

        self._max_num_pages = max_num_pages
        self._max_file_size_bytes = (
            max_file_size_mb * 1024 * 1024
        )
        self._mapper = mapper or DoclingCanonicalMapper()

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = enable_ocr
        pipeline_options.do_table_structure = enable_tables

        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            },
        )

    @property
    def document_format(self) -> DocumentFormat:
        return DocumentFormat.NATIVE_PDF

    def supports(
        self,
        source: DocumentSource,
    ) -> bool:
        return source.file_path.suffix.lower() == ".pdf"

    def ingest(
        self,
        source: DocumentSource,
    ) -> CanonicalDocument:
        if not source.file_path.exists():
            raise FileNotFoundError(
                f"PDF for PID '{source.pid}' does not exist: "
                f"{source.file_path}"
            )

        try:
            result = self._converter.convert(
                source.file_path,
                max_num_pages=self._max_num_pages,
                max_file_size=self._max_file_size_bytes,
            )
        except Exception as exc:
            raise ValueError(
                f"Docling failed to convert PID '{source.pid}'"
            ) from exc

        return self._mapper.map_document(
            docling_document=result.document,
            document_id=source.pid,
            source_path=str(source.file_path),
            document_format=self.document_format,
            metadata={},
        )