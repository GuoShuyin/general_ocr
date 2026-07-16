# Chinese Document OCR API

[中文文档](./README.zh-CN.md)

An OCR service for extracting structured information from Chinese business and identity documents, designed to remain robust to rotation, perspective distortion, and layout variation. The project combines PaddleOCR with OpenCV preprocessing and document-specific parsing rules, then exposes the capability through a Flask HTTP API.

## What I built

- A Flask API that accepts images and PDFs and returns structured OCR results.
- Image-preprocessing routines for rotation and orientation correction.
- Improved robustness to rotation, perspective distortion, and layout variation with document-specific preprocessing and extraction rules.
- Document-specific extraction for invoices, Chinese ID cards, bank cards, and license plates.
- English API field names for downstream integrations, while preserving Chinese document support.
- Table-to-Excel and document-to-DOCX conversion workflows.
- A Docker-based deployment configuration for the original project environment.

## Supported workflows

| Input | Output |
| --- | --- |
| Chinese invoices, ID cards, bank cards, and license plates | Structured JSON fields |
| Images and PDFs | OCR text and extracted document data |
| Tables | Excel workbook |
| Documents | Reconstructed DOCX file |

## API overview

The service entry point is [`general_API_service.py`](./general_API_service.py). It exposes a `POST /ocr` endpoint that accepts a file and document type.

```bash
curl -X POST "http://localhost:5000/ocr?type=invoice" \
  -F "file=@sample_invoice.png"
```

Available document types include `invoice`, `id_card`, `bank_card`, `license_plate`, `excel`, and `document`.

> Do not use real identity documents, bank-card data, or invoices in public demos. Use synthetic or fully redacted samples only.

## Repository guide

- [`general_API_service.py`](./general_API_service.py): Flask routes and request handling.
- [`general_ocr_API.py`](./general_ocr_API.py): OCR orchestration and document-specific extraction.
- [`general_ocr.py`](./general_ocr.py): original OCR implementation and preprocessing utilities.
- [`generalOCR接口使用文档.pdf`](./generalOCR接口使用文档.pdf): Chinese API reference.
- [`通用识别使用开发文档.pdf`](./通用识别使用开发文档.pdf): Chinese development guide.

The Chinese-language documents are retained because this project was built for Chinese document workflows. This README is the English entry point for reviewers and collaborators.

## Local setup

This is an archived project and its original environment used Python 3.7. Install the Python dependencies and the Poppler system package required by `pdf2image` before running the API:

```bash
python -m pip install -r requirements.txt
# macOS: brew install poppler
# Ubuntu/Debian: sudo apt-get install poppler-utils
```

The bundled inference assets and deployment scripts reflect the project's original environment. A clean-environment smoke test and Docker configuration refresh are planned before treating the repository as a production-ready package.

## Attribution

This project uses [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) and its related inference assets for OCR capabilities. PaddleOCR and any copied upstream components remain subject to their respective licenses; see [`NOTICE.md`](./NOTICE.md). The application API, preprocessing workflow, and document-specific extraction logic in this repository are project work by Shuyin Guo.
