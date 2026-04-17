# FairHire AI 🚀

FairHire AI is a state-of-the-art SaaS application built to enforce equitable hiring workflows, surface complex demographic bias patterns natively inside datasets, and process advanced candidate profiles utilizing massive-scale Machine Learning tools out-of-the-box. 

![FairHire AI Dashboard](https://img.shields.io/badge/Status-Production_Ready-brightgreen)
![React](https://img.shields.io/badge/Frontend-React.js-blue)
![Flask](https://img.shields.io/badge/Backend-Flask_Python-red)
![MongoDB](https://img.shields.io/badge/Database-MongoDB_Atlas-green)

---

## 🌟 Key Features

### 1. **V3 Universal ML Fairness Engine & SHAP Explainability**
Upload **any arbitrary CSV file**, and FairHire AI will structurally detect your target demographic natively! It autonomously scrubs missing components, scales categorical algorithms using advanced `sklearn` ColumnTransformers, and bridges raw matrix variances straight into **SHAP (Shapley Additive Explanations)**! See *exactly* what factors mathematically drove an applicant's success visually (e.g. `education: 0.32`).

### 2. **Generative Candidate Analysis (Gemini 3.1 Pro)**
The system intelligently bridges unstructured Word (`.docx`) and Acrobat (`.pdf`) resume variants—extracting skills natively and mapping them directly to strict tier scoring algorithms. The integrated **Google Gemini 3.1 Pro** model natively constructs pristine executive demographic summaries dynamically!

### 3. **Intelligent Job Matching**
FairHire AI maps isolated candidate JSON variables structurally across real-world enterprise architectures leveraging the Adzuna intelligence API—linking remote jobs directly to users based on calculated score constraints and location targeting parameters. 

### 4. **Military-Grade Security Hardening**
* **MongoDB Rolling Rate Limiters:** Flask natively calculates 60-second execution boundaries shielding internal workers from unauthenticated API scraping overloads via ephemeral Atlas tracking. 
* **HttpOnly Session Cookies:** Cross-Site Scripting (XSS) leaks are intrinsically walled off as React securely accepts global `SameSite=Lax` cookie bindings without relying on primitive `localStorage` JSON blobs.
* **Zip-Bomb Safety Buffers:** Infinite looping payload anomalies masking as XML bombs are forcefully eradicated mid-stream by capping internal PDF text-buffers natively.

---

## 🛠️ Technology Stack

* **Frontend:** React (Context API, Lucide Icons, Axios Interceptors)
* **Backend:** Flask / Python 3 / Flask-JWT-Extended
* **Machine Learning:** `scikit-learn` (Generic AI mapping), `shap` (Feature Explainability), `pandas`
* **Generative NLP:** Google GenAI SDK (Gemini 3.1 Pro Preview)
* **Database Platform:** MongoDB Atlas

---

## 💻 Running Locally

### 1. Requirements
* PyMongo (must support Atlas DNS sequences via `pymongo[srv]`)
* Node.js v16+
* Python 3.10+

### 2. Environment Variables (.env)
Clone the repository and add the following keys to a root `.env` string:
```bash
SECRET_KEY=your_secure_string_here
MONGO_URI=mongodb+srv://<auth>@your_atlas_cluster.mongodb.net/?appName=appName
GEMINI_API_KEY=your_gemini_token
ADZUNA_APP_ID=adzuna_id
ADZUNA_APP_KEY=adzuna_key
```

### 3. Application Start Sequence
Run the native builder to launch everything over dual developer ports quickly:
```bash
# 1. Boot the Flask Core Route
python -m pip install -r requirements.txt
python app.py

# 2. Boot the React GUI Application
cd frontend-react
npm install
npm start
```

---

## ☁️ Deployment (Render / Heroku)

This application has been successfully decoupled into a robust static monolith! Python natively consumes and hosts the unified React GUI framework meaning you only configure one cloud service! 

1. Create a **New Web Service** inside Render.com.
2. Link your current Github branch directly!
3. **Build Command:** `./build.sh`
4. **Start Command:** `gunicorn app:app`
5. Inject the `.env` parameters explicitly into the web portal. 

*FairHire AI — Empowering equitable sourcing decisions at absolute scale.*
