from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import io
from docx import Document
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TailorRequest(BaseModel):
    resume: str
    job_description: str

@app.post("/tailor")
async def tailor_resume(request: TailorRequest):
    prompt = f"""
You are a resume expert. Improve and tailor the following resume for this job description.

Job Description:
{request.job_description}

Resume:
{request.resume}

Tailor and rewrite the resume to match the job, keeping it professional and ATS-optimized.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4"
            messages=[
                {"role": "system", "content": "You are a helpful assistant skilled in resume tailoring."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        tailored_resume = response.choices[0].message.content
        return {"tailored_resume": tailored_resume}
    except Exception as e:
        return {"error": str(e)}

@app.post("/tailor-file")
async def tailor_file(file: UploadFile = File(...), job_description: str = Form(...)):
    try:
        contents = await file.read()
        if file.filename.endswith(".docx"):
            doc = Document(io.BytesIO(contents))
            resume_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            return {"error": "Unsupported file type. Please upload a .docx file."}

        prompt = f"""
You are a resume expert. Improve and tailor the following resume for this job description.

Job Description:
{job_description}

Resume:
{resume_text}

Tailor and rewrite the resume to match the job, keeping it professional and ATS-optimized.
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4"
            messages=[
                {"role": "system", "content": "You are a helpful assistant skilled in resume tailoring."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        tailored_resume = response.choices[0].message.content
        return {"tailored_resume": tailored_resume}

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
