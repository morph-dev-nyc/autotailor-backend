from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from docx import Document as DocxDocument
import io
import os
import json
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile
import re

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
You are a professional resume editor.

Your task is to slightly rephrase and reorganize the ORIGINAL RESUME content below to improve clarity, flow, and alignment with the JOB DESCRIPTION. 

IMPORTANT:
- You MUST NOT invent any content, certifications, experiences, job titles, tools, or achievements that are not present in the original resume.
- DO NOT add assumptions or guesses based on the job description.
- DO NOT infer anything not explicitly stated.
- The only acceptable changes are rewording existing phrases, optimizing structure, and emphasizing relevant points.
- Each job entry should contain up to 5 bullet points MAX.
- Total output should be around 500 words (±10%).
- If no certifications were in the original resume, leave that section out.
- Never add extra bullets for titles/companies/dates.

JOB DESCRIPTION:
{job_description}

ORIGINAL RESUME:
{resume_text}

Output a valid JSON with these fields:
- "contact": string
- "summary": short paragraph
- "skills": newline-separated bullets
- "experience": list of objects ("title", "company", "date", "bullets")
- "education": string
- "certifications": string (only if present originally)

ONLY return valid JSON with no extra text.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a resume editing assistant that only improves and rephrases existing content without inventing anything."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "Failed to parse GPT response as JSON."}


def create_formatted_docx(structured: dict) -> io.BytesIO:
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
                if bullet.strip():
                    doc.add_paragraph(bullet.strip(), style='List Bullet')

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


def sanitize_header(value: str) -> str:
    return ''.join(c for c in value if ord(c) < 128)  # Remove non-ASCII characters


def clean_filename_part(text: str) -> str:
    # Remove non-alphanumeric characters except spaces and dashes
    text = re.sub(r'[^\w\s-]', '', text)
    # Normalize whitespace and strip
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def make_filename(full_name: str, job_title: str, company: str) -> str:
    full_name_clean = clean_filename_part(full_name)
    job_title_clean = clean_filename_part(job_title)
    company_clean = clean_filename_part(company)

    # If job title is already in full_name, don't repeat it
    if job_title_clean.lower() in full_name_clean.lower():
        parts = [full_name_clean]
    else:
        parts = [full_name_clean, job_title_clean]

    if company_clean and company_clean.lower() not in (full_name_clean + job_title_clean).lower():
        parts.append(company_clean)

    filename = "_".join(parts) + ".docx"
    # Replace spaces with underscores (optional, safer for filenames)
    filename = filename.replace(' ', '_')

    return filename


@app.post("/tailor-file")
async def tailor_file(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    linkedin_company: str = Form(""),
    linkedin_title: str = Form("")
):
    content = await file.read()

    if file.filename.endswith(".docx"):
        with NamedTemporaryFile(delete=True, suffix=".docx") as tmp:
            tmp.write(content)
            tmp.flush()
            doc = DocxDocument(tmp.name)
            resume_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    else:
        resume_text = content.decode("utf-8", errors="ignore")

    structured_resume = generate_structured_resume(resume_text, job_description)
    if "error" in structured_resume:
        return {"error": structured_resume["error"]}

    contact = structured_resume.get("contact", "")
    full_name = ""
    if contact:
        lines = [line.strip() for line in contact.splitlines() if line.strip()]
        if lines:
            full_name = lines[0]

    buffer = create_formatted_docx(structured_resume)

    filename = make_filename(full_name, linkedin_title, linkedin_company)

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Full-Name": sanitize_header(full_name),
            "X-LinkedIn-Company": sanitize_header(linkedin_company),
            "X-LinkedIn-Title": sanitize_header(linkedin_title),
        }
    )
