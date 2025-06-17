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
    CORSMidådleware,
    allow_origins=["*"],  # Set to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_structured_resume(resume_text: str, job_description: str) -> dict:
    prompt = f"""
You are a professional technical resume writer.

Your task is to improve the wording and structure of the ORIGINAL RESUME below to better align with the JOB DESCRIPTION provided.

STRICT GUIDELINES:
- DO NOT invent any new experience, roles, certifications, or skills that are not already in the original resume.
- ONLY rephrase and reorganize existing content to better match the job description.
- DO NOT fabricate credentials, employers, or projects.
- Each job description must be summarized in NO MORE THAN 5 bullet points.
- The total word count of the final resume should be approximately 500 words (±10%).
- DO NOT add bullets for job titles/companies/dates—only for actual responsibilities or achievements.
- Preserve all actual experience, education, and skills, but tailor the wording for relevance.
- If the original resume contains no certifications, the "certifications" field should be left empty or omitted.

JOB DESCRIPTION:
{job_description}

ORIGINAL RESUME:
{resume_text}

Format your final result as a clean structured JSON object with the following keys:
- "contact": a one-line string
- "summary": a short summary paragraph
- "skills": newline-separated bullet point skills
- "experience": a list of objects with "title", "company", "date", and "bullets" (list of bullet points, max 5 each)
- "education": a one-line or multi-line string
- "certifications": a string (only if mentioned in original resume)

Return ONLY valid JSON with no code blocks or explanation.
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
            doc.add_paragraph(f"{role.get('title')} – {role.get('company')} ({role.get('date')})")
            for bullet in role.get("bullets", [])[:5]:
                doc.add_paragraph(bullet, style='List Bullet')

    if education := structured.get("education"):
        doc.add_heading("Education", level=2)
        doc.add_paragraph(education)

    if certs := structured.get("certifications"):
        if certs.strip():  # only include if non-empty
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
