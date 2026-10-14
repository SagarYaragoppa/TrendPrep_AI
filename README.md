# AI Question Paper Organizer

A fully local AI-powered web workflow to organize PYQs (Previous Year Questions) from PDFs and Images. 

## Features
- Upload multiple PDFs or Images in bulk
- Syllabus-driven topic and subtopic organization
- Relevant-paper selection for bundled university PDFs
- Local-first classification with optional Gemini assistance
- Automated de-duplication and source-year merging
- `Clean`, `Full`, or `Both` output download modes
- Structured PDF output ready for revision

## Prerequisites
1. **Python 3.10+** (installed and added to path)
2. **Gemini API Key**: Optional. Used to improve classification quality when available.
3. *(Optional for Image OCR)*: **Tesseract OCR**. Install from https://github.com/UB-Mannheim/tesseract/wiki and add to Windows PATH.

## Setup Instructions
1. Open up `backend/.env` file and put your Gemini API Key:
   ```env
   GEMINI_API_KEY="your-gemini-api-key-here"
   ```
2. Double-click the `start.bat` file in the root directory.
3. This will start the FastAPI backend and automatically open the UI in your web browser.
4. Choose an output mode in the UI:
   - `Clean organized PDF`
   - `Full preserve-all PDF`
   - `Download both`

## Deployment Notes
- The frontend calls the backend with a relative `/api/upload` path, so it is safer to deploy behind a single host/reverse proxy.
- If Tesseract is not available, the app still works for text PDFs and skips OCR-only pages instead of crashing.
- For best generic performance on new subjects, upload the syllabus together with all related PYQ PDFs.

## Tech Stack
- **Backend:** Python, FastAPI, PyMuPDF, Pytesseract, Gemini SDK (`google-genai`), FPDF2
- **Frontend:** Vanilla HTML, Vanilla CSS (Glassmorphism design), Vanilla JS
