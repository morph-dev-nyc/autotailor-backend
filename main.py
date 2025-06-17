from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from docx import Document
import io
import os
from dotenv import load_dotenv

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
You are an expert resume writer. Rewrite and polish the original resume below to better match the job description.

Job Description:
{job_description}

Original Resume:
{resume_text}

Instructions:
- Keep the resume structure and include only experiences from the original resume.
- Tailor descriptions and phrasing to better align with the job description.
- Use a clean format with one-line contact info, and clear sections: Summary, Skills, Experience, Education, Certifications.
- Remove excess spacing and formatting characters like asterisks, markdown, or backticks.
- Return plain text only, formatted for Word output.
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
    resume_text = content.decode("utf-8", errors="ignore")

    tailored_text = generate_tailored_resume(resume_text, job_description)

    doc = Document()
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