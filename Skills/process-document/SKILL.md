---
name: process-document
description: Read and extract text from PDF, Word, TXT, and other documents. Use this when user asks to read, extract, parse, or summarize a document file.
metadata:
  author: youngstunners.zo.computer
---

# Process Document Skill

Use this skill when the user wants to read, extract, parse, or summarize documents.

## Supported Formats
- **PDF**: `.pdf` files - use read_file with pdf_epub parameters
- **Word**: `.docx`, `.doc` files  
- **Text**: `.txt`, `.md`, `.csv`
- **EPUB**: `.epub` files

## Usage

### Reading a PDF
```
read_file(target_file="/path/to/file.pdf", pdf_epub_start_page=1, pdf_epub_end_page=10)
```

### Reading a Word doc
```
read_file(target_file="/path/to/file.docx")
```

### Extracting text from PDF in Python
```python
from pypdf import PdfReader
reader = PdfReader("file.pdf")
text = "\n".join([page.extract_text() for page in reader.pages])
```

## Tools
- read_file: For direct file reading
- run_bash_command: For Python scripts with pypdf or python-docx