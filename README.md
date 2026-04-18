# FairHire AI — Bias Detection & Mitigation Platform 🚀

[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)](https://fairhire-ai.com)
[![Backend](https://img.shields.io/badge/Backend-Flask%20%2B%20Python-red)](https://flask.palletsprojects.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React.js-blue)](https://react.dev/)
[![Database](https://img.shields.io/badge/Database-MongoDB-green)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 Problem Statement

Artificial intelligence is increasingly used for hiring decisions, loan approvals, and other critical life outcomes. However, **AI bias** remains a pervasive problem:

- **Hiring:** ML models perpetuate historical discrimination based on gender, race, age
- **Loans:** Algorithms deny credit to protected groups at higher rates
- **Scale:** Biased decisions compound across millions of individuals

**FairHire AI** solves this by detecting, mitigating, and explaining bias in AI systems before they cause harm.

---

## 💡 Solution

FairHire AI is a comprehensive platform that:

### 1. **Detects Bias** 🔍

- Uploads any CSV dataset
- Analyzes demographic disparities using fairness metrics
- Identifies which features drive biased outcomes
- Calculates fairness scores (0-100)

### 2. **Fixes Bias** ⚙️

- Applies reweighting, SMOTE oversampling, correlation removal
- Optimizes decision thresholds per demographic group
- Ensures accuracy doesn't suffer significantly from mitigation
- Rolls back unsafe changes automatically

### 3. **Explains Decisions** 📊

- Uses SHAP (Shapley Additive Explanations) for per-instance interpretability
- Shows which features contributed to each prediction
- Flags sensitive attributes that influenced decisions
- Provides human-readable summaries

### 4. **Real-Time Firewall** 🛡️

- Evaluates individual predictions for bias risk
- Flags high-risk decisions before they're acted upon
- Detects group disparities in real time
- Provides actionable recommendations

---

## 🌟 Key Features

| Feature             | Description                                                                      |
| ------------------- | -------------------------------------------------------------------------------- |
| **Dataset Audit**   | Comprehensive data quality and bias pre-flight checks                            |
| **Bias Detection**  | Advanced fairness metrics (demographic parity, equalized odds, disparate impact) |
| **Bias Mitigation** | Multi-step mitigation pipeline with safety rollback                              |
| **Explainability**  | SHAP-based instance-level feature importance                                     |
| **Bias Firewall**   | Real-time prediction monitoring and flagging                                     |
| **Full Analysis**   | Single-endpoint orchestration of entire bias lifecycle                           |
| **Gemini AI**       | NLP-powered summaries and recommendations                                        |
| **User Management** | JWT authentication, rate limiting, audit logs                                    |

---

## 🛠️ Technology Stack

### Backend

- **Framework:** Flask (Python 3.10+)
- **ML:** scikit-learn, pandas, numpy
- **Fairness:** SHAP, custom fairness metrics
- **Bias Mitigation:** imbalanced-learn (SMOTE), scipy
- **Database:** MongoDB Atlas
- **Auth:** Flask-JWT-Extended, bcrypt
- **AI:** Google GenAI SDK (Gemini 3.1 Pro)

### Frontend

- **Framework:** React 18 (Context API for state)
- **Styling:** Tailwind CSS, PostCSS
- **HTTP:** Axios with interceptors
- **Icons:** Lucide React
- **File Upload:** React Dropzone

### Deployment

- **Backend:** Gunicorn on Render
- **Frontend:** React static build on Render/Netlify
- **Database:** MongoDB Atlas (serverless)
- **Environment:** `.env` file for secrets

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+
- MongoDB Atlas account
- Google GenAI API key

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/fairhire-ai.git
   cd fairhire-ai
   ```

2. **Backend setup**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment configuration**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - MONGO_URI
   # - GEMINI_API_KEY
   # - JWT_SECRET_KEY
   ```

4. **Frontend setup**

   ```bash
   cd frontend-react
   npm install
   npm run build
   cd ..
   ```

5. **Run locally**

   ```bash
   # Terminal 1: Backend
   python app.py

   # Terminal 2: Frontend (for development)
   cd frontend-react
   npm start
   ```

Visit `http://localhost:3000` and the API at `http://localhost:5000`.

---

## ⚡ Try It in 60 Seconds

Don't want to set up the full stack? Test bias detection instantly:

1. **Start the backend:**

   ```bash
   python app.py
   ```

2. **In another terminal, run:**

   ```bash
   curl -X POST http://localhost:5000/full-analysis \
     -F "file=@sample_data_hiring.csv"
   ```

3. **Expected output (in ~10 seconds):**
   - Dataset audit results
   - Fairness score **before mitigation**: ~42 (High Risk)
   - Fairness score **after mitigation**: ~68 (Moderate Risk)
   - Human-readable summary explaining bias reduction
   - AI-generated recommendations

**The entire bias detection → mitigation → explanation pipeline in one request.**

---

## 📡 API Endpoints

### Core Analysis

| Endpoint         | Method | Description                                                   |
| ---------------- | ------ | ------------------------------------------------------------- |
| `/analyze`       | POST   | Detect bias in dataset                                        |
| `/mitigate`      | POST   | Run bias mitigation pipeline                                  |
| `/full-analysis` | POST   | Complete bias lifecycle (audit → detect → mitigate → explain) |

### Supporting

| Endpoint          | Method         | Description                                    |
| ----------------- | -------------- | ---------------------------------------------- |
| `/firewall`       | POST           | Real-time bias risk evaluation for predictions |
| `/auth/register`  | POST           | Create user account                            |
| `/auth/login`     | POST           | Login with email/password                      |
| `/profile`        | GET/PUT/DELETE | Manage user profile                            |
| `/resume/analyze` | POST           | Extract and score resume                       |
| `/jobs`           | GET            | Search jobs (Adzuna API)                       |

### Example Request: Full Analysis

```bash
curl -X POST http://localhost:5000/full-analysis \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@dataset.csv" \
  -F "sensitive_columns=gender,race,age"
```

### Example Response

```json
{
  "audit": {
    "warnings": [
      {
        "type": "CLASS_IMBALANCE",
        "message": "Target variable imbalance: 35% positive, 65% negative",
        "severity": "INFO"
      }
    ],
    "summary": "Dataset audit completed with 1 warning.",
    "severity": "INFO",
    "severity_counts": { "INFO": 1 },
    "details": {
      "missing_values": 0,
      "duplicate_rows": 0,
      "sensitive_columns_detected": ["gender", "age"],
      "proxy_variables": [
        {
          "feature": "years_experience",
          "sensitive_attribute": "age",
          "correlation": 0.78,
          "severity": "CRITICAL"
        }
      ]
    }
  },
  "before": {
    "fairness_score": 42,
    "bias_level": "High Risk",
    "accuracy": 0.78,
    "metrics": {
      "demographic_parity_gap_gender": 0.22,
      "equalized_odds_tpr_gap": 0.18,
      "disparate_impact_ratio": 0.68
    }
  },
  "after": {
    "fairness_score": 68,
    "bias_level": "Moderate Risk",
    "accuracy": 0.76,
    "metrics": {
      "demographic_parity_gap_gender": 0.08,
      "equalized_odds_tpr_gap": 0.06,
      "disparate_impact_ratio": 0.92
    }
  },
  "improvement": "Mitigation completed with 4 steps: correlation_removal, smote, reweighting, threshold_optimization",
  "risk_transition": "High Risk → Moderate Risk",
  "impact_statement": "The model was 22% less likely to hire female candidates. After bias mitigation, this gap reduced to 8%, significantly improving fairness while maintaining 76% accuracy.",
  "recommendations": [
    "Continue monitoring demographic parity gaps quarterly",
    "Review hiring criteria to reduce proxy variable influence (years_experience correlates 0.78 with age)",
    "Implement human review process for borderline predictions (confidence < 0.65)",
    "Rebalance training data collection to avoid historical hiring bias"
  ],
  "human_summary": "The dataset audit showed bias in High Risk. After mitigation, risk moved from High Risk → Moderate Risk and fairness improved by +26 points. This means the model is now safer to use but should remain monitored for bias drift."
}
```

---

## 🏗️ Project Structure

```
fairhire-ai/
├── app.py                 # Main Flask application
├── bias_detector.py       # Bias analysis orchestration
├── gemini_helper.py       # Gemini API integration
├── config.py              # Configuration & environment
├── database.py            # MongoDB operations
├── auth.py                # JWT authentication
├── requirements.txt       # Python dependencies
├── Procfile               # Render deployment config
├── build.sh               # Build script
│
├── ml/
│   ├── pipeline.py        # ML training & fairness scoring
│   └── __init__.py
│
├── services/
│   ├── dataset_auditor.py # Pre-flight data quality checks
│   ├── mitigation.py      # Bias mitigation engine
│   ├── explainer.py       # SHAP-based explanations
│   ├── bias_firewall.py   # Real-time bias detection
│   ├── cache.py           # Model caching
│   ├── workflow.py        # Mitigation orchestration
│   └── __init__.py
│
├── fairness/
│   ├── metrics.py         # Fairness metric computations
│   ├── scoring.py         # Overall fairness scoring
│   └── __init__.py
│
├── frontend-react/
│   ├── public/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── contexts/      # Auth/state contexts
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── tailwind.config.js
│
└── README.md              # This file
```

---

## 🧪 Testing

### Manual Testing

```bash
# Test bias detection
curl -X POST http://localhost:5000/analyze \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@test_data.csv"

# Test full pipeline
curl -X POST http://localhost:5000/full-analysis \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@test_data.csv"
```

---

## 🚢 Deployment

### Deploy to Render

1. **Connect GitHub repository to Render**
2. **Set environment variables:**
   - `MONGO_URI`
   - `GEMINI_API_KEY`
   - `JWT_SECRET_KEY`
   - `FLASK_ENV=production`

3. **Configure build command:**

   ```bash
   bash build.sh
   ```

4. **Configure start command:**

   ```bash
   gunicorn app:app
   ```

5. **Deploy**
   - Render auto-deploys on `git push origin main`

---

## 📊 How It Works

### Bias Detection Pipeline

1. **Load Data:** Parse CSV, validate structure
2. **Audit:** Check for quality issues, missing values, class imbalance
3. **Train Model:** Logistic regression or Random Forest
4. **Compute Fairness:** Calculate demographic parity, equalized odds, disparate impact
5. **Generate Summary:** Human-readable insights

### Bias Mitigation Pipeline

1. **Baseline:** Establish current performance/fairness
2. **Correlation Removal:** De-correlate features from sensitive attributes
3. **SMOTE:** Oversample underrepresented groups
4. **Reweighting:** Adjust sample weights by group
5. **Threshold Optimization:** Find group-specific decision boundaries
6. **Rollback:** If accuracy drops > threshold, revert to baseline
7. **Post-Evaluation:** Re-compute fairness on mitigated model

### Explainability Flow

1. **SHAP Values:** Compute Shapley values for each feature
2. **Feature Contributions:** Quantify impact of each attribute
3. **Sensitive Flag:** Alert if protected attributes influenced decision
4. **Human Summary:** Generate natural language explanation

---

## 🔐 Security

- **Password Hashing:** bcrypt with salt
- **JWT Tokens:** HttpOnly, SameSite=Lax cookies
- **Rate Limiting:** MongoDB-backed, 10 requests per 60 seconds per user
- **Input Validation:** File size limits, MIME type checking
- **File Cleanup:** Automatic removal of old uploads
- **Environment Secrets:** `.env` file (never committed)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📈 Future Scope

- **Real-Time Monitoring:** Dashboard for ongoing bias drift detection
- **Enterprise Integration:** SSO, SAML, audit logging
- **Custom Metrics:** Allow users to define fairness objectives
- **Model Registry:** Version control for trained models
- **Batch Processing:** Asynchronous analysis jobs
- **Webhooks:** Integration with ATS systems (Workday, Greenhouse, etc.)
- **Compliance Reports:** GDPR, CCPA, EO-compliant audits

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Your Name** — Full Stack Engineer

---

## 📞 Support

For questions or issues:

- Open an issue on GitHub
- Email: support@fairhire-ai.com
- Documentation: [https://docs.fairhire-ai.com](https://docs.fairhire-ai.com)

---

## 🙏 Acknowledgments

- [scikit-learn](https://scikit-learn.org/) for ML framework
- [SHAP](https://github.com/slundberg/shap) for explainability
- [MongoDB](https://www.mongodb.com/) for database
- [Gemini API](https://ai.google.dev/) for AI summaries
- [React](https://react.dev/) for frontend framework

---

**Made with ❤️ for fair hiring and equitable AI**
