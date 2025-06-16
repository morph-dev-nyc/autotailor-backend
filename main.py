from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
from docx import Document
from io import BytesIO
import os
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_file(file: UploadFile) -> str:
    if file.filename.endswith(".txt"):
        return file.file.read().decode("utf-8")
    elif file.filename.endswith(".docx"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        doc = Document(tmp_path)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        raise ValueError("Unsupported file format. Please upload .txt or .docx files.")

def generate_tailored_resume(job_description: str, resume_text: str) -> str:
    prompt = (
        "You are a professional resume writer. Tailor the following resume for this job description.\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Resume:\n{resume_text}\n\n"
        "Return only the tailored resume, formatted professionally."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message.content

@app.post("/tailor-file")
async def tailor_resume_file(file: UploadFile = File(...), job_description: str = Form(...)):
    try:
        resume_text = extract_text_from_file(file)
        tailored_resume = generate_tailored_resume(job_description, resume_text)

        doc = Document()
        for line in tailored_resume.split('\n'):
            doc.add_paragraph(line)

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=tailored_resume.docx"}
        )
    except Exception as e:
        return {"error": str(e)}
