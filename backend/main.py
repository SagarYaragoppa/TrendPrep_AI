from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import io
import zipfile

try:
    from extractor import extract_text, extract_questions_from_text, extract_relevant_text
    from classifier import classify_question
    from deduplicator import add_question, format_source_label
    from document_generator import generate_pdf
except ImportError:
    from backend.extractor import extract_text, extract_questions_from_text, extract_relevant_text
    from backend.classifier import classify_question
    from backend.deduplicator import add_question, format_source_label
    from backend.document_generator import generate_pdf

app = FastAPI(title="AI Question Paper Organizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    syllabus: str = Form(...),
    output_mode: str = Form("clean")
):
    organized_data = {}
    
    for file in files:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())
            
        try:
            text = extract_relevant_text(temp_path, syllabus)
            questions = extract_questions_from_text(text)
            
            for q in questions:
                classification = classify_question(q, syllabus)
                topic = classification["topic"]
                subtopic = classification["subtopic"]
                if classification.get("route") == "review":
                    topic = "Appendix - Needs Review"
                    confidence = classification.get("confidence", "low").title()
                    subtopic = f"{confidence} Confidence"
                source = format_source_label(file.filename)
                add_question(q, source, topic, subtopic, organized_data)
                
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    clean_data = {
        topic: subtopics
        for topic, subtopics in organized_data.items()
        if not topic.startswith("Appendix")
    }

    if output_mode == "full":
        pdf_io = generate_pdf(organized_data)
        filename = "organized_papers_full.pdf"
    elif output_mode == "both":
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("organized_papers_clean.pdf", generate_pdf(clean_data).getvalue())
            zf.writestr("organized_papers_full.pdf", generate_pdf(organized_data).getvalue())
        archive.seek(0)
        return StreamingResponse(
            archive,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=organized_papers_bundle.zip"},
        )
    else:
        pdf_io = generate_pdf(clean_data)
        filename = "organized_papers_clean.pdf"

    pdf_io.seek(0)
    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
