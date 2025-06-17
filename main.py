from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from docx import Document as DocxDocument
import io
import os
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

def clean_gpt_response(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    cleaned = [line for line in lines if line and not line.startswith("```")]
    return "\n".join(cleaned)

def generate_tailored_resume(resume_text: str, job_description: str) -> str:
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
- Reword the resume using industry language and terminology from the job description without adding fake experience.
- Emphasize achievements and duties that are most relevant to the job description.
- Remove excess spacing, markdown formatting, or characters like asterisks, backticks, or triple dashes.
- Use a clean and modern layout:
  • One-line contact info at the top
  • Sections: Summary, Skills, Experience, Education, Certifications
  • Use plain text bullets (•) where appropriate
  • Format the result as plain text that can be easily converted to Word (.docx)

Return ONLY the final rewritten resume in plain text. Do not include any commentary, code blocks, or explanations.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful and detail-oriented resume rewriting assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    raw_text = response.choices[0].message.content.strip()
    return clean_gpt_response(raw_text)

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

    tailored_text = generate_tailored_resume(resume_text, job_description)

    doc = DocxDocument()
    for line in tailored_text.split("\n"):
        doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=tailored_resume.docx"}
    )
