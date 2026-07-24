from __future__ import annotations

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)

from src.canonical.docling_mapper import DoclingCanonicalMapper
from src.canonical.model import (
    CanonicalDocument,
    DocumentFormat,
)
from src.ingest.base import FormatAdapter
from src.ingest.source import DocumentSource

from docling.backend.pypdfium2_backend import (
    PyPdfiumDocumentBackend,
)
class DoclingPDFAdapter(FormatAdapter):
    

    def __init__(
        self,
        *,
        enable_ocr: bool = True,
        enable_tables: bool = False,
        minimum_native_elements: int = 5,
        max_num_pages: int = 100,
        max_file_size_mb: int = 50,
        mapper: DoclingCanonicalMapper | None = None,
    ) -> None:
        if minimum_native_elements < 0:
            raise ValueError(
                "minimum_native_elements cannot be negative"
            )

        if max_num_pages <= 0:
            raise ValueError(
                "max_num_pages must be positive"
            )

        if max_file_size_mb <= 0:
            raise ValueError(
                "max_file_size_mb must be positive"
            )

        self._enable_ocr = enable_ocr
        self._enable_tables = enable_tables
        self._minimum_native_elements = (
            minimum_native_elements
        )

        self._max_num_pages = max_num_pages
        self._max_file_size_bytes = (
            max_file_size_mb * 1024 * 1024
        )

        self._mapper = mapper or DoclingCanonicalMapper()

        # Native extraction is lightweight and should always be
        # attempted before loading OCR models.
        self._native_converter = self._build_converter(
            enable_ocr=False
        )

        # OCR converter is created lazily only when native extraction
        # does not produce enough content.
        self._ocr_converter: DocumentConverter | None = None

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
        self._validate_source(source)

        try:
            native_document = self._convert_and_map(
                source=source,
                converter=self._native_converter,
                extraction_method="native",
            )
        except ValueError as native_error:
            if not self._enable_ocr:
                raise

            print(
                f"Native extraction failed for PID "
                f"'{source.pid}'. Retrying with OCR..."
            )

            if self._ocr_converter is None:
                self._ocr_converter = self._build_converter(
                    enable_ocr=True,
                )

            try:
                return self._convert_and_map(
                    source=source,
                    converter=self._ocr_converter,
                    extraction_method="ocr",
                )
            except ValueError as ocr_error:
                raise ValueError(
                    f"Both native and OCR extraction failed "
                    f"for PID '{source.pid}'."
                ) from ocr_error

        native_element_count = self._element_count(
            native_document
        )

        if (
            not self._enable_ocr
            or native_element_count
            >= self._minimum_native_elements
        ):
            return native_document

        print(
            "Native extraction produced only "
            f"{native_element_count} elements for "
            f"PID '{source.pid}'. Retrying with OCR..."
        )

        if self._ocr_converter is None:
            self._ocr_converter = self._build_converter(
                enable_ocr=True,
            )

        return self._convert_and_map(
            source=source,
            converter=self._ocr_converter,
            extraction_method="ocr",
        )

    def _build_converter(
        self,
        *,
        enable_ocr: bool,
    ) -> DocumentConverter:
        pipeline_options = PdfPipelineOptions()

        pipeline_options.do_ocr = enable_ocr
        pipeline_options.do_table_structure = False

        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False
        pipeline_options.generate_parsed_pages = False

        pipeline_options.images_scale = 0.25

        pipeline_options.ocr_batch_size = 1
        pipeline_options.layout_batch_size = 1
        pipeline_options.table_batch_size = 1
        pipeline_options.queue_max_size = 1

        if not enable_ocr:
            pipeline_options.force_backend_text = True

        return DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            },
        )

    def _convert_and_map(
        self,
        *,
        source: DocumentSource,
        converter: DocumentConverter,
        extraction_method: str,
    ) -> CanonicalDocument:
        try:
            result = converter.convert(
                source.file_path,
                max_num_pages=self._max_num_pages,
                max_file_size=self._max_file_size_bytes,
            )
        except Exception as exc:
            raise ValueError(
                "Docling failed to convert "
                f"PID '{source.pid}' using "
                f"{extraction_method} extraction"
            ) from exc

        metadata = {
            **getattr(source, "metadata", {}),
            "extraction_method": extraction_method,
            "ocr_used": extraction_method == "ocr",
        }

        return self._mapper.map_document(
            docling_document=result.document,
            document_id=source.pid,
            source_path=str(source.file_path),
            document_format=self.document_format,
            metadata=metadata,
        )

    def _validate_source(
        self,
        source: DocumentSource,
    ) -> None:
        file_path = Path(source.file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"PDF for PID '{source.pid}' does not exist: "
                f"{file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"PDF path is not a file: {file_path}"
            )

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(
                "DoclingPDFAdapter only supports PDF files: "
                f"{file_path}"
            )

        file_size = file_path.stat().st_size

        if file_size > self._max_file_size_bytes:
            raise ValueError(
                f"PDF exceeds the configured file-size limit: "
                f"{file_path}"
            )

    @staticmethod
    def _element_count(
        document: CanonicalDocument,
    ) -> int:
        # Use the property if your canonical model defines it.
        element_count = getattr(
            document,
            "element_count",
            None,
        )

        if isinstance(element_count, int):
            return element_count

        # Safe fallback when the model has no element_count property.
        return sum(
            len(page.elements)
            for page in document.pages
        )