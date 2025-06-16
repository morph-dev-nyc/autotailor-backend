# AutoTailor Backend

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Add your OpenAI key to the `.env` file:
```env
OPENAI_API_KEY=your_key_here
```

4. Run the server:
```bash
uvicorn main:app --reload
```

## Endpoint

- POST `/tailor`
  - `resume`: str
  - `job_description`: str
