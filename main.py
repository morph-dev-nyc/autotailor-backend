from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
from docx import Document

app = FastAPI()

# Enable CORS for your frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for testing, restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/tailor-file")
async def tailor_file(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    if not job_description or job_description.strip() == "":
        raise HTTPException(status_code=422, detail="job_description is required")

    # Read uploaded file bytes
    contents = await file.read()

    # For demonstration, let's create a new .docx that contains:
    # - The original filename
    # - The job description text
    # - A placeholder for "tailored content"
    doc = Document()
    doc.add_heading("Tailored Resume", level=1)
    doc.add_paragraph(f"Original filename: {file.filename}")
    doc.add_paragraph("Job Description:")
    doc.add_paragraph(job_description)
    doc.add_paragraph("\n---\nTailored content goes here based on resume and job description.")

    # You would put your actual tailoring logic here instead of the above

    # Save to in-memory bytes buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Return the docx file as a streaming response
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=tailored_resume.docx"
        },
    )
