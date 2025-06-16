from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import openai
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant skilled in resume tailoring."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return {"tailored_resume": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}
