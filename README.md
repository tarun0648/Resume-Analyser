# Resume Processor

A powerful, AI-driven resume processing and analysis tool. Upload resumes (PDF), extract structured information, generate tailored interview questions, and analyze job fit using advanced AI models. Integrates with Firebase for storage and logging.

---

## ✨ Features

- **Resume Upload & Extraction:**  
  Upload PDF resumes and extract structured data (personal info, skills, experience, education, projects, certifications).

- **Job Description Matching:**  
  Compare resumes against job descriptions using AI (Claude) to generate a match score, summary, strengths, gaps, and recommendations.

- **Interview Question Generation:**  
  Automatically generate tailored interview questions based on the candidate's resume and experience.

- **Batch Processing:**  
  Upload and process multiple resumes at once against a single job description.

- **Comprehensive Reports:**  
  Get detailed JSON reports for each resume, including extracted data, interview questions, and job match analysis.

- **Firebase Integration:**  
  Store processing results and files securely in Firebase.

- **Logging:**  
  All actions and errors are logged to `backend/logs/app.log` for easy debugging.

- **Command-Line & Web Interface:**  
  Use the web frontend or run analyses via the command line.

---


https://github.com/user-attachments/assets/e6f6a8aa-cfc5-45c5-9b83-0d3414f05b04



## 🚀 Getting Started

### 1. Clone the Repository

```sh
git clone <your-repo-url>
cd "resume processor/backend"
```

### 2. Set Up Python Virtual Environment

```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```sh
pip install -r requirements.txt
```

### 4. Configure Environment Variables

- Copy `.env.example` to `.env` (if provided) and fill in your credentials.
- Ensure you have a valid `serviceAccountKey.json` for Firebase in the `backend/` directory.

**Required environment variables:**
- `CLAUDE_API_KEY`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_PRIVATE_KEY`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_STORAGE_BUCKET`
- (See `backend/config.py` for details.)

### 5. Run Backend Server

```sh
python main.py
```

### 6. Run Frontend

- Open `frontend/index.html` directly in your browser  
  **OR**  
- Serve it locally:
  ```sh
  cd ../frontend
  python -m http.server 8000
  ```
  Then visit [http://localhost:8000](http://localhost:8000).

---

## 🧪 Testing

- Run setup tests:
  ```sh
  python test_setup.py
  ```
- Run all backend tests:
  ```sh
  python fix.py
  ```

---

## 📝 Usage

- **Web:**  
  Use the frontend to upload resumes and view results.
- **API:**  
  POST to `/upload-resume` with a PDF and optional job description.
- **Batch:**  
  POST to `/batch-upload` with multiple PDFs and a job description.
- **Command Line:**  
  See `resume_summarizer.py` for CLI usage.

---

## 📁 Project Structure

```
backend/
  main.py                # Flask API server
  resume_extractor_cl.py # Resume extraction logic
  resume_summarizer.py   # Job matching & analysis
  resume_questions.py    # Interview question generation
  config.py              # Configuration & environment
  requirements.txt       # Python dependencies
  serviceAccountKey.json # Firebase credentials
  logs/app.log           # Log file
frontend/
  index.html             # Web interface
```

---





## 🛠️ Deployment

- For Docker or Nginx deployment, see `backend/deploy.sh` and `backend/nginx.conf`.

---

## 📢 Notes

- Only PDF resumes are supported.
- Maximum file size: 16MB (configurable).
- Requires internet access for AI and Firebase features. 
