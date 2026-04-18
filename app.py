from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity, set_access_cookies, unset_jwt_cookies
from bias_detector import analyze_bias
from services.workflow import run_bias_mitigation_workflow
from services.bias_firewall import firewall_check
from gemini_helper import generate_impact_statement, generate_fix_plan
import os
import uuid
import logging
import pandas as pd
from report_generator import generate_report
from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    LOG_LEVEL, LOG_FILE,
    DEFAULT_DATASET_PATH,
    UPLOAD_FOLDER, REPORT_FOLDER,
    MAX_FILE_SIZE
)
from auth import init_jwt, login_user, register_user, user_required
from database import Analysis, Report, User, History, db_manager, init_indexes
from werkzeug.utils import secure_filename
import time
from resume_analyzer import analyze_resume
from job_matcher import match_candidate

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_orphaned_uploads():
    try:
        cutoff = time.time() - 3600
        for folder in [UPLOAD_FOLDER, REPORT_FOLDER]:
            if not os.path.exists(folder):
                continue
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) and file_path.lower().endswith(('.csv', '.pdf', '.docx')):
                    if os.path.getmtime(file_path) < cutoff:
                        os.remove(file_path)
    except Exception as e:
        logger.error(f"Garbage collector failure: {e}")

def validate_file(file, allowed_extensions, max_size=MAX_FILE_SIZE):
    if not file:
        return {"valid": False, "error": "No file provided"}

    filename = secure_filename(file.filename)
    if not filename:
        return {"valid": False, "error": "Invalid filename"}

    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in allowed_extensions:
        return {"valid": False, "error": f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"}

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > max_size:
        return {"valid": False, "error": f"File too large. Max size: {max_size // (1024*1024)}MB"}

    # MIME type check
    mime = file.mimetype if hasattr(file, 'mimetype') else None
    if mime:
        if ext == 'csv' and mime not in ['text/csv', 'application/csv', 'text/plain', 'application/vnd.ms-excel', 'application/octet-stream']:
            return {"valid": False, "error": "Invalid CSV file"}
        elif ext == 'pdf' and mime != 'application/pdf':
            return {"valid": False, "error": "Invalid PDF file"}
        elif ext == 'docx' and mime not in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return {"valid": False, "error": "Invalid DOCX file"}

    return {"valid": True, "filename": filename}

# ---------------- STATIC HOSTING (REACT) ----------------
FRONTEND_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend-react', 'build')

app = Flask(__name__, static_url_path='/react_static_bypass', static_folder=FRONTEND_FOLDER)
# Restrict CORS to localhost and future prod URL
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://fairhire-prod-url.ai"])

API_PREFIXES = (
    "auth/",
    "analyze",
    "mitigate",
    "full-analysis",
    "report",
    "firewall",
    "resume",
    "job",
    "history",
    "health",
    "profile",
)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    from flask import send_from_directory
    if path.startswith(API_PREFIXES):
        return jsonify({"error": "Not found"}), 404
    if not os.path.isdir(FRONTEND_FOLDER):
        if path:
            return jsonify({"error": "Frontend build not found"}), 404
        return jsonify({"status": "FairHire API Running"}), 200
    if path != "" and os.path.exists(os.path.join(FRONTEND_FOLDER, path)):
        return send_from_directory(FRONTEND_FOLDER, path)
    else:
        return send_from_directory(FRONTEND_FOLDER, 'index.html')

# ---------------- JWT ----------------
init_jwt(app)
with app.app_context():
    try:
        init_indexes()
    except Exception as e:
        logger.warning(f"Index initialization skipped: {e}")

# ---------------- RATE LIMIT ----------------
from database import RateLimit

def check_rate_limit(user_id, endpoint, limit=10, window=60):
    return RateLimit.check(user_id, endpoint, limit, window)


# ---------------- AUTH ----------------
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password required"}), 400

    client_id = data.get('email', request.remote_addr)
    if not check_rate_limit(client_id, 'login', limit=5, window=300):
        return jsonify({"error": "Too many login attempts. Try again in 5 minutes."}), 429

    result = login_user(data['email'], data['password'])

    if not result:
        return jsonify({"error": "Invalid email or password"}), 401
    
    response = jsonify(result)
    set_access_cookies(response, result["access_token"])
    return response, 200


@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password required"}), 400

    result = register_user(data['email'], data['password'])

    if not result:
        return jsonify({"error": "Email already exists"}), 400

    response = jsonify(result)
    set_access_cookies(response, result["access_token"])
    return response, 201


@app.route('/auth/logout', methods=['POST'])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response, 200


# ---------------- PROFILE ----------------
@app.route('/profile', methods=['GET'])
@user_required
def get_profile():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()

    profile = User.get_profile(user_id)
    if not profile:
        return jsonify({"error": "User not found"}), 404

    return jsonify(profile), 200


@app.route('/profile', methods=['PUT'])
@user_required
def update_profile():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    updated = User.update_profile(user_id, data)
    if not updated:
        return jsonify({"error": "Update failed"}), 500

    return jsonify(updated), 200


@app.route('/profile', methods=['DELETE'])
@user_required
def delete_profile():
    from flask_jwt_extended import get_jwt_identity, unset_jwt_cookies
    user_id = get_jwt_identity()

    deleted = User.delete(user_id)
    if not deleted:
        return jsonify({"error": "Delete failed"}), 500

    response = jsonify({"msg": "Profile deleted"})
    unset_jwt_cookies(response)
    return response, 200


# ---------------- ANALYZE ----------------
@app.route('/analyze', methods=['POST'])
@user_required
def analyze():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    cleanup_orphaned_uploads()

    if not check_rate_limit(user_id, 'analyze'):
        return jsonify({"error": "Rate limit exceeded"}), 429

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    validation = validate_file(file, ['csv'])
    if not validation['valid']:
        return jsonify({"error": validation['error']}), 400

    filename = secure_filename(f"{uuid.uuid4()}.csv")
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    try:
        result = analyze_bias(str(file_path), user_id=user_id, save_to_db=True)
        History.create(
            user_id=user_id, 
            op_type="bias_detection", 
            input_meta={"filename": filename, "dataset_info": result.get('dataset_info', {})}, 
            output_results={"fairness_score": result.get('fairness_score')}
        )
        logger.info(f"Analysis completed for user {user_id}, score: {result.get('fairness_score', 'N/A')}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Analysis failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.route('/mitigate', methods=['POST'])
@user_required
def mitigate():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    cleanup_orphaned_uploads()

    if not check_rate_limit(user_id, 'mitigate'):
        return jsonify({"error": "Rate limit exceeded"}), 429

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    validation = validate_file(file, ['csv'])
    if not validation['valid']:
        return jsonify({"error": validation['error']}), 400

    filename = secure_filename(f"{uuid.uuid4()}.csv")
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    sensitive_columns = None
    if 'sensitive_columns' in request.form:
        raw = request.form.get('sensitive_columns', '')
        sensitive_columns = [col.strip() for col in raw.split(',') if col.strip()]

    try:
        df = pd.read_csv(file_path)
        if sensitive_columns:
            df_cols = set(df.columns.tolist())
            sensitive_columns = [col for col in sensitive_columns if col in df_cols]
        result = run_bias_mitigation_workflow(df, sensitive_cols=sensitive_columns)
        History.create(
            user_id=user_id,
            op_type="bias_mitigation",
            input_meta={"filename": filename, "dataset_info": result.get('before', {})},
            output_results={
                "fairness_before": result.get('before', {}).get('fairness_score'),
                "fairness_after": result.get('fairness_after')
            }
        )
        logger.info(f"Mitigation completed for user {user_id}, before {result.get('before', {}).get('fairness_score')}, after {result.get('fairness_after')}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Mitigation failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.route('/full-analysis', methods=['POST'])
@user_required
def full_analysis():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    cleanup_orphaned_uploads()

    if not check_rate_limit(user_id, 'full_analysis'):
        return jsonify({"error": "Rate limit exceeded"}), 429

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    validation = validate_file(file, ['csv'])
    if not validation['valid']:
        return jsonify({"error": validation['error']}), 400

    filename = secure_filename(f"{uuid.uuid4()}.csv")
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    sensitive_columns = None
    if 'sensitive_columns' in request.form:
        raw = request.form.get('sensitive_columns', '')
        sensitive_columns = [col.strip() for col in raw.split(',') if col.strip()]

    try:
        df = pd.read_csv(file_path)
        if sensitive_columns:
            df_cols = set(df.columns.tolist())
            sensitive_columns = [col for col in sensitive_columns if col in df_cols]
        result = analyze_bias(
            str(file_path),
            user_id=user_id,
            save_to_db=True,
            run_mitigation=True,
            sensitive_columns=sensitive_columns
        )

        mitigation_result = result.get('mitigation', {})
        bias_payload = {
            "fairness_score": result.get('fairness_score', 100.0),
            "gender_bias": result.get('gender_bias', {}),
            "age_bias": {},
            "race_bias": {},
            "education_bias": {}
        }

        impact = generate_impact_statement(bias_payload)
        plan = generate_fix_plan(bias_payload)

        before = result.get('before', {})
        after = mitigation_result.get('after', {})
        improvement = mitigation_result.get('improvement', 'Mitigation completed.')
        risk_transition = mitigation_result.get('risk_transition', 'No change')

        before_level = before.get('bias_level', before.get('bias_summary', {}).get('bias_level', 'Unknown'))
        after_level = after.get('risk_level', after.get('bias_level', 'Unknown'))
        fairness_before = before.get('fairness_score', result.get('fairness_score', 0.0))
        fairness_after = after.get('fairness_score', fairness_before)
        human_summary = (
            f"The dataset audit showed bias in {before_level}. "
            f"After mitigation, risk moved from {before_level} to {after_level} and fairness improved by {fairness_after - fairness_before:.2f}. "
            f"This means the model is now safer to use but should remain monitored."
        )

        full_result = {
            "audit": result.get('audit', {}),
            "before": before,
            "after": after,
            "improvement": improvement,
            "risk_transition": risk_transition,
            "impact_statement": impact.get('impact', ''),
            "recommendations": plan.get('fix_plan', []),
            "human_summary": human_summary,
            "verdict": result.get("mitigation", {}).get("verdict", {}),
        }

        History.create(
            user_id=user_id,
            op_type="full_analysis",
            input_meta={"filename": filename, "dataset_info": result.get('dataset_info', {})},
            output_results={
                "fairness_before": fairness_before,
                "fairness_after": fairness_after
            }
        )

        logger.info(f"Full analysis completed for user {user_id}, before {fairness_before}, after {fairness_after}")
        return jsonify(full_result)
    except Exception as e:
        logger.error(f"Full analysis failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ---------------- REPORT ----------------
@app.route('/report', methods=['POST'])
@user_required
def report():
    cleanup_orphaned_uploads()
    user_id = get_jwt_identity()

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        file_path = generate_report(data)
        Report.create(user_id, str(file_path))
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Report error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/report/download/<report_id>', methods=['GET'])
@user_required
def download_report(report_id):
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()

    report = Report.find_by_id(report_id)

    if not report:
        return jsonify({"error": "Report not found"}), 404

    if report.get("user_id") != user_id:
        return jsonify({"error": "Access denied"}), 403

    file_path = report.get("file_path")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Report file not found on server"}), 404

    return send_file(file_path, as_attachment=True, download_name=report.get("file_name", "fairhire_report.pdf"))


# ---------------- FIREWALL ----------------
@app.route('/firewall', methods=['POST'])
@user_required
def firewall():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No input data"}), 400

    bias_file = str(DEFAULT_DATASET_PATH)

    try:
        bias_data = analyze_bias(bias_file)
        result = firewall_check(data, bias_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Firewall failed: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------- RESUME ----------------
@app.route('/resume/analyze', methods=['POST'])
@user_required
def resume_route():
    cleanup_orphaned_uploads()
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    validation = validate_file(file, ['pdf', 'docx'])
    if not validation['valid']:
        return jsonify({"error": validation['error']}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    try:
        from flask_jwt_extended import get_jwt_identity
        from database import User
        user_id = get_jwt_identity()

        result = analyze_resume(str(file_path))
        
        # Store resume data into context
        User.update_resume_data(user_id, result)
        
        # Track History
        History.create(
            user_id=user_id,
            op_type="resume_analysis",
            input_meta={"filename": filename},
            output_results={"resume_score": result.get("resume_score", 0)}
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        import gc
        gc.collect()


# ---------------- JOB MATCH ----------------
@app.route('/job/match', methods=['POST'])
@user_required
def job_matcher_route():
    cleanup_orphaned_uploads()
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    validation = validate_file(file, ['pdf', 'docx'])
    if not validation['valid']:
        return jsonify({"error": validation['error']}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    try:
        from resume_analyzer import analyze_resume, extract_text_from_file
        from job_matcher import fetch_jobs, match_candidate
        
        # 1. extract text and analyze
        resume_text = extract_text_from_file(str(file_path))
        analysis_result = analyze_resume(str(file_path))
        skills = analysis_result.get('skills', [])

        if not skills:
            skills = ['software'] # Fallback
            
        # 2. fetch jobs based on skills
        # Get location and limit from form data if provided
        location = request.form.get('location', 'us')
        limit = min(int(request.form.get('limit', 10)), 20)
        
        jobs_data = fetch_jobs(skills, location=location, limit=limit)
        jobs = jobs_data.get('jobs', [])

        # 3. score each job against the resume text
        scored_jobs = []
        for job in jobs:
            match_result = match_candidate(resume_text, job.get('description', ''))
            job['match_score'] = match_result.get('overall_match_score', 0)
            job['match_category'] = match_result.get('match_category', 'Unknown')
            scored_jobs.append(job)

        scored_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        top_match_score = scored_jobs[0]['match_score'] if scored_jobs else 0
        
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        History.create(
            user_id=user_id,
            op_type="job_match",
            input_meta={"filename": filename, "skills": skills},
            output_results={"top_match_score": top_match_score, "jobs_found": len(scored_jobs)}
        )

        return jsonify({
            "jobs": scored_jobs, 
            "match_score": top_match_score
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.route('/job/fetch', methods=['POST'])
@user_required
def job_fetch():
    data = request.get_json() or {}

    from flask_jwt_extended import get_jwt_identity
    from database import User
    
    user_id = get_jwt_identity()
    user = User.find_by_id(user_id)

    if not user or "resume_data" not in user or "skills" not in user["resume_data"]:
        return jsonify({"error": "No resume found. Please upload a resume first."}), 400

    skills = user["resume_data"]["skills"]

    if not skills:
        return jsonify({"error": "No specific skills detected in your previous resume upload."}), 400

    location = data.get('location', 'us')
    limit = min(int(data.get('limit', 5)), 10)  # Max 10

    try:
        from job_matcher import fetch_jobs
        result = fetch_jobs(skills, location, limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- HISTORY ----------------
@app.route('/history', methods=['GET'])
@user_required
def get_user_history():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()

    history = History.find_by_user(user_id)
    return jsonify(history)


# ---------------- HEALTH ----------------
@app.route('/health')
def health():
    try:
        db_manager.ensure_connection()
        db_manager.client.admin.command('ping')
        return jsonify({"status": "OK", "db": "connected"})
    except Exception as e:
        return jsonify({"status": "degraded", "db": str(e)}), 503


@app.route('/')
def home():
    return "FairHire API Running 🚀"


# ---------------- RUN ----------------
if __name__ == '__main__':
    logger.info(f"Starting server at {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
