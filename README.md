# 📄 Document Delta & Grounded Chat

An AI-assisted system for comparing technical document revisions and answering grounded questions over the detected changes.

The project extracts structured elements from engineering documents, aligns content across revisions, classifies semantic differences,
 and produces an explainable delta report that can be queried through a grounded chat interface.

Built as part of an Applied AI engineering assessment, the system emphasizes modular architecture, reproducible evaluation, and explainable
 outputs rather than simple document diffing.

## Overview

Engineering documents such as P&IDs, CAD drawings, and technical PDFs evolve through multiple revisions. Traditional text comparison tools are unable to distinguish meaningful engineering changes from formatting differences or positional shifts.

This project provides an AI-assisted comparison pipeline that:

- extracts structured document elements
- aligns corresponding elements across revisions
- classifies additions, removals, modifications, and movements
- generates a structured delta report
- enables grounded question answering over both document revisions and the generated report

The system is designed to be modular, extensible, and suitable for production-oriented AI workflows.

## Features

- Native PDF document ingestion
- Canonical document representation
- Element-level alignment
- Semantic change classification
- Structured JSON delta reports
- Significant vs. insignificant change filtering
- FastAPI REST API
- Streamlit web interface
- Grounded chat over document revisions
- Evaluation framework
- Comprehensive unit tests

## Architecture


                   +--------------------+
                   |  Original Document |
                   +--------------------+
                             │
                             ▼
                     Document Ingestion
                             │
                             ▼
                    Canonical Document
                             │
                             │
                   +--------------------+
                   | Revised Document   |
                   +--------------------+
                             │
                             ▼
                     Document Ingestion
                             │
                             ▼
                    Canonical Document
                             │
                             ▼
                    Element Alignment
                             │
                             ▼
                  Change Classification
                             │
                             ▼
                     Delta Report (JSON)
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
        Evaluation                   Grounded Chat

## Design Principles

The project separates the document-processing pipeline into independent stages:

- ingestion
- alignment
- comparison
- reporting
- question answering

This separation makes each component independently testable and allows alternative implementations (different OCR engines, 
embedding models, or alignment strategies) without changing the rest of the pipeline.

## Repository Structure

```text
Document-Delta-Grounded-Chat/
│
├── data/
│   ├── samples/                 # Sample input documents
│   └── evaluation/              # Ground truth datasets
│
├── outputs/
│   ├── uploads/                 # Uploaded documents
│   ├── api_reports/             # Generated delta reports
│   └── evaluation/              # Evaluation results
│
├── scripts/
│   ├── compare_revisions.py
│   └── evaluate.py
│
├── src/
│   ├── api/                     # FastAPI application
│   ├── ingestion/               # Document parsing
│   ├── alignment/               # Element matching
│   ├── comparison/              # Change classification
│   ├── reporting/               # Delta report generation
│   ├── chat/                    # Grounded question answering
│   ├── models/                  # Pydantic domain models
│   └── evaluation/              # Evaluation pipeline
│
├── tests/                       # Unit tests
│
├── ui/
│   └── streamlit_app.py         # Streamlit frontend
│
├── requirements.txt
├── README.md
└── LICENSE
```

## Technology Stack

| Category | Technology |
|----------|------------|
| Programming Language | Python 3.11 |
| Backend API | FastAPI |
| Frontend | Streamlit |
| Data Validation | Pydantic v2 |
| Document Processing | Docling |
| AI / Embeddings | Sentence Transformers |
| Similarity Search | FAISS |
| Testing | Pytest |
| Server | Uvicorn |
| Data Exchange | JSON |

## Design Decisions

### Canonical Representation

Instead of comparing documents directly, every input document is transformed into a common canonical representation.
 This decouples document ingestion from downstream processing and allows new document formats to be added without 
 changing the alignment or comparison pipeline.

### Deterministic Delta Engine

The delta engine uses deterministic alignment and comparison algorithms rather than an LLM. This ensures reproducible
 outputs, consistent evaluation, and avoids hallucinated changes.

### Grounded Chat

The chat layer retrieves only information present in the generated delta report and returns answers with citations.
 This guarantees traceability and prevents unsupported responses.

## Trade-offs

To keep the implementation focused, the project prioritizes:

- Native PDF support over implementing all formats.
- Deterministic retrieval over LLM-based generation.
- Structured JSON reports instead of visual markup overlays.
- Modular architecture over UI complexity.

These choices improve reproducibility, simplify evaluation, and make the system easier to extend.

## Current Limitations

- OCR accuracy depends on scan quality.
- Retrieval is keyword-based rather than embedding-based.
- Only native PDF ingestion is fully implemented.
- Visual delta markup is not included.

## Evaluation

The repository includes an evaluation framework for measuring:

- Delta precision
- Delta recall
- Delta F1
- Grounded answer correctness
- Citation accuracy

Evaluation datasets are located in:

data/evaluation/

### Project Organization

The repository follows a modular architecture in which each stage of the document-processing pipeline is implemented 
as an independent component.

- **ingestion** transforms source documents into a canonical representation.
- **alignment** identifies corresponding elements between document revisions.
- **comparison** classifies additions, removals, modifications, and movements.
- **reporting** generates structured JSON delta reports.
- **chat** provides grounded question answering over the generated reports.
- **evaluation** measures the quality of change detection and grounded responses.

This separation keeps the codebase maintainable, testable, and extensible while allowing individual components to 
evolve independently.

## Installation

### Clone the repository

```bash
git clone https://github.com/<your-username>/document-delta-grounded-chat.git
cd document-delta-grounded-chat
```

### Create a virtual environment

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Project

### Start the FastAPI server

```bash
uvicorn src.api.main:app --reload
```

API documentation:

```
http://127.0.0.1:8000/docs
```

---

### Launch the Streamlit interface

```bash
streamlit run ui/streamlit_app.py
```

The Streamlit application will be available at:

```
http://localhost:8501
```

## API Documentation

The backend exposes REST endpoints for document comparison and report retrieval.

### Base URL

```
http://127.0.0.1:8000
```

---

### Health Check

**GET** `/health`

Checks whether the API is running.

#### Response

```json
{
  "status": "healthy"
}
```

---

### Compare Document Revisions

**POST** `/delta/compare`

Uploads two document revisions, performs element alignment and change detection, and returns a structured delta report.

#### Request

| Parameter | Type | Description |
|-----------|------|-------------|
| before_file | File | Original document |
| after_file | File | Revised document |

#### Response

```json
{
  "success": true,
  "report_id": "...",
  "summary": {
    "total_changes": 524,
    "added": 183,
    "removed": 48,
    "modified": 174,
    "moved": 64,
    "moved_and_modified": 55
  }
}
```

---

### Retrieve a Delta Report

**GET** `/delta/{report_id}`

Returns the complete JSON delta report for a previously generated comparison.

#### Response

```json
{
  "report_id": "...",
  "summary": { ... },
  "changes": [ ... ]
}
```

---

### Interactive API Documentation

FastAPI automatically generates Swagger UI documentation.

Open:

```
http://127.0.0.1:8000/docs
```

to explore and test the API directly from your browser.

## Streamlit Interface

The project includes a lightweight Streamlit application that provides an interactive interface for document comparison.

### Workflow

1. Upload the original document.
2. Upload the revised document.
3. Click **Compare Documents**.
4. View the generated summary of detected changes.
5. Browse the detailed change list.
6. (Optional) Ask grounded questions about the detected changes.

The Streamlit interface communicates with the FastAPI backend, which performs document ingestion, alignment, change detection, and report generation.

## Delta Report Generation

After comparing the original and revised documents, the system generates a structured JSON delta report.

Each report contains:

- a unique report identifier
- summary counts for each change type
- significant element-level changes
- before and after content
- element metadata
- evidence used by the grounded chat service

Generated reports are stored in:

```text
outputs/api_reports/