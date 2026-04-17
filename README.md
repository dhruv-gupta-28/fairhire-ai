# FairHire AI - Hiring Bias Detection & Mitigation System

A production-ready Flask API for detecting and mitigating algorithmic bias in hiring decisions using machine learning and fairness metrics.

## Features

- **🔍 Bias Detection**: Multi-dimensional fairness analysis (gender, age, race, education)
- **🛡️ Firewall System**: Real-time candidate fairness checking before hiring decisions
- **📊 Advanced Metrics**: 6-metric fairness evaluation with severity assessment
- **🚀 Mitigation Strategies**: Reweighing, threshold optimization, post-processing adjustment
- **📈 ML Pipeline**: Logistic regression model with fair predictions
- **🤖 AI Integration**: Gemini-powered bias reduction suggestions (optional)
- **📄 Report Generation**: PDF/JSON audit reports with breakdowns
- **🔒 Security**: Input validation, file type checking, path traversal protection
- **📝 Logging**: Structured logging with configurable levels

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd fairhire-ai

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env` file in project root (optional):

```env
GEMINI_API_KEY=your-api-key-here
LOG_LEVEL=INFO
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
```

Without Gemini API key, the system falls back to rule-based recommendations.

### Running the API

```bash
# Development server
python app.py

# Production server (gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Testing the API

1. **Health Check**:

   ```bash
   curl http://localhost:5000/health
   ```

2. **Bias Analysis** (upload CSV file):

   ```bash
   curl -X POST -F "file=@data.csv" http://localhost:5000/analyze
   ```

3. **Firewall Check**:

   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"age": 30, "sex": "Female"}' \
        http://localhost:5000/firewall
   ```

4. **Generate Report**:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d @analysis_result.json \
        http://localhost:5000/report \
        --output report.pdf
   ```

## API Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `POST /analyze` - Upload CSV and analyze bias
- `POST /firewall` - Check candidate fairness
- `POST /report` - Generate downloadable PDF report

## Frontend

The system includes a modern web interface:

```bash
# Serve frontend (open frontend/index.html in browser)
# Or use a static file server
python -m http.server 8000 -d frontend/
```

Navigate to `http://localhost:8000` to access the dashboard.

## Data Format

The system expects CSV files with the following columns (no headers):

- age, workclass, fnlwgt, education, education_num, marital_status, occupation, relationship, race, sex, capital_gain, capital_loss, hours_per_week, native_country, income

Example data can be obtained from [UCI Adult Dataset](https://archive.ics.uci.edu/dataset/2/adult).

## Architecture

```
fairhire-ai/
├── app.py                 # Flask API server
├── bias_detector.py       # Core bias analysis logic
├── firewall.py           # Real-time fairness checking
├── gemini_helper.py      # AI-powered suggestions
├── report_generator.py   # PDF/JSON report generation
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── frontend/
│   └── index.html        # Web dashboard
├── fairness/             # Fairness metrics module
│   ├── __init__.py
│   ├── metrics.py        # 6 fairness metrics
│   └── scoring.py        # Scoring and aggregation
├── mitigation/           # Bias mitigation strategies
│   ├── __init__.py
│   └── bias_mitigation.py # Threshold optimization
└── ml/                   # Machine learning pipeline
    ├── __init__.py
    └── pipeline.py       # Model training and prediction
```

## Security Features

- File upload validation (CSV only)
- Path traversal protection
- Input sanitization for all endpoints
- Configurable dataset paths
- Structured logging for monitoring

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
pytest
```

### Code Quality

```bash
# Lint code
pip install flake8
flake8 .

# Format code
pip install black
black .
```

## License

MIT License - see LICENSE file for details.

````

Server runs on `http://localhost:5000`

## API Endpoints

### 1. Analyze Bias

**POST** `/analyze`

Upload a hiring dataset CSV to analyze bias patterns.

```bash
curl -X POST -F "file=@data.csv" http://localhost:5000/analyze
````

**Response**: Fairness scores, gender/age/race/education bias metrics, recommendations

### 2. Firewall Check

**POST** `/firewall`

Check if a candidate would be discriminated against based on protected characteristics.

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "age": 32,
    "sex": "Female",
    "race": "Asian-Pac-Islander",
    "education": "Bachelors",
    "bias_file": "data.csv"
  }' \
  http://localhost:5000/firewall
```

**Response**: `FAIR` or `BIASED` verdict with detailed gap analysis

### 3. Generate Report

**POST** `/report`

Generate PDF audit report with fairness breakdown.

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"fairness_score": 73.04, ...}' \
  http://localhost:5000/report
```

### 4. Health Check

**GET** `/health`

System status endpoint.

## System Architecture

```
┌─────────────────────────────────┐
│      Flask API Layer            │
│  (/analyze, /firewall, /report) │
├─────────────────────────────────┤
│    ML Pipeline + Fairness       │
│  (LogisticRegression + Metrics) │
├─────────────────────────────────┤
│  Bias Detection & Mitigation    │
│  (Gender, Age, Race, Education) │
└─────────────────────────────────┘
```

## File Structure

```
fairhire-ai/
├── app.py                    # Flask entry point
├── bias_detector.py          # Core bias analysis
├── firewall.py               # Real-time fairness checking
├── gemini_helper.py          # AI-powered suggestions
├── report_generator.py       # Report generation
│
├── ml/
│   ├── __init__.py
│   └── pipeline.py           # ML model training & prediction
│
├── fairness/
│   ├── __init__.py
│   ├── metrics.py            # 6-metric fairness evaluation
│   └── scoring.py            # Aggregated fairness scoring
│
└── mitigation/
    ├── __init__.py
    └── bias_mitigation.py    # Bias reduction techniques
```

## Fairness Metrics

The system evaluates 6 industry-standard fairness dimensions:

1. **Demographic Parity**: Equal selection rates across groups
2. **Equalized Odds**: Equal error rates (TPR & FPR) across groups
3. **Disparate Impact**: 80% rule compliance
4. **Calibration**: Predicted probabilities match actual outcomes
5. **TPR Parity**: Equal true positive rates
6. **FPR Parity**: Equal false positive rates

**Thresholds**:

- Difference < 0.10: ACCEPTABLE ✅
- Difference 0.10-0.15: WARNING ⚠️
- Difference > 0.15: CRITICAL 🚨

## Fairness Score

Aggregate score (0-100) computed as:

$$\text{FairnessScore} = 100 \times \left(1 - \frac{\text{Gender Gap} + \text{Age Gap} + \text{Race Gap} + \text{Education Gap}}{4}\right)$$

**Score Interpretation**:

- 80-100: Excellent fairness
- 60-80: Acceptable fairness
- 40-60: Poor fairness
- 0-40: Critical unfairness

## Protected Characteristics

The system analyzes bias across:

- **Gender**: Male, Female
- **Age Groups**: Young (<30), Mid (30-49), Senior (≥50)
- **Race**: 5 categories (Amer-Indian-Eskimo, Asian-Pac-Islander, Black, Other, White)
- **Education**: Basic, Intermediate, Advanced
- **Occupation**: Reported for context (not in fairness score)

## Security & Compliance

- ✅ Path traversal prevention (file validation)
- ✅ CORS enabled for React frontend integration
- ✅ Concurrent upload safety (UUID-based temp files)
- ✅ Automatic temp file cleanup
- ✅ No credential leakage

## Production Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Environment Variables

```env
FLASK_ENV=production
GEMINI_API_KEY=your-key-here
```

## Testing

```bash
# Run test suite
pytest tests/

# Test specific endpoint
curl http://localhost:5000/health
```

## Contributing

1. Maintain backward compatibility
2. Keep fairness metrics aligned with industry standards
3. Add tests for new features
4. Document API changes

## License

Proprietary - FairHire AI

## Support

For issues or questions, contact the FairHire team.
