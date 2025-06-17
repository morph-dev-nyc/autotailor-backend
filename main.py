from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from docx import Document as DocxDocument
import io
import os
import json
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_structured_resume(resume_text: str, job_description: str) -> dict:
    prompt = f"""
You are a professional technical resume writer.

Your task is to take the ORIGINAL RESUME below and improve it to align with the JOB DESCRIPTION provided.

JOB DESCRIPTION:
{job_description}

ORIGINAL RESUME:
{resume_text}

Rewrite the resume using these instructions:

- ONLY use experience, education, and skills from the original resume.
- Modify job titles, bullet points, and descriptions so that they align with responsibilities and keywords from the job description.
- Emphasize achievements and duties that are most relevant to the job description.
- Return a clean structured JSON object with the following keys: "contact", "summary", "skills", "experience", "education", "certifications".
- Each section should be a string (except experience which should be a list of roles with title, company, date, bullets).

Return only the JSON, no explanations or formatting.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful and detail-oriented resume rewriting assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "Failed to parse GPT response as JSON."}

def create_formatted_docx(structured: dict) -> bytes:
    doc = DocxDocument()

    if contact := structured.get("contact"):
        doc.add_paragraph(contact)

    if summary := structured.get("summary"):
        doc.add_heading("Summary", level=2)
        doc.add_paragraph(summary)

    if skills := structured.get("skills"):
        doc.add_heading("Skills", level=2)
        for skill in skills.split("\n"):
            if skill.strip():
                doc.add_paragraph(skill.strip(), style='List Bullet')

    if experience := structured.get("experience"):
        doc.add_heading("Experience", level=2)
        for role in experience:
            doc.add_paragraph(f"{role.get('title')} – {role.get('company')} ({role.get('date')})", style='List Bullet')
            for bullet in role.get("bullets", []):
                doc.add_paragraph(bullet, style='List Bullet 2')

    if education := structured.get("education"):
        doc.add_heading("Education", level=2)
        doc.add_paragraph(education)

    if certs := structured.get("certifications"):
        doc.add_heading("Certifications", level=2)
        doc.add_paragraph(certs)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

@app.post("/tailor-file")
async def tailor_file(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    content = await file.read()

    if file.filename.endswith(".docx"):
        with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(content)
            tmp.flush()
            doc = DocxDocument(tmp.name)
            resume_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    else:
        resume_text = content.decode("utf-8", errors="ignore")

    structured_resume = generate_structured_resume(resume_text, job_description)
    if "error" in structured_resume:
        return {"error": structured_resume["error"]}

    buffer = create_formatted_docx(structured_resume)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=tailored_resume.docx"}
    )
