from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity, set_access_cookies, unset_jwt_cookies
from bias_detector import analyze_bias
from firewall import firewall_check
import os
import uuid
import logging
from report_generator import generate_report
from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    LOG_LEVEL, LOG_FILE,
    DEFAULT_DATASET_PATH,
    UPLOAD_FOLDER, REPORT_FOLDER,
    MAX_FILE_SIZE
)
from auth import init_jwt, login_user, register_user, user_required
from database import Analysis, Report, User, History
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

app = Flask(__name__, static_folder='frontend-react/build', static_url_path='/')
# Restrict CORS to localhost and future prod URL
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://fairhire-prod-url.ai"])

# ---------------- STATIC HOSTING (REACT) ----------------
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    from flask import send_from_directory
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# ---------------- JWT ----------------
init_jwt(app)

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


# ---------------- REPORT ----------------
@app.route('/report', methods=['POST'])
@user_required
def report():
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

    bias_file = data.get("bias_file", str(DEFAULT_DATASET_PATH))

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


# ---------------- JOB MATCH ----------------
@app.route('/job/match', methods=['POST'])
@user_required
def job_match():
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
        limit = int(request.form.get('limit', 10))
        
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
    return jsonify({"status": "OK"})


@app.route('/')
def home():
    return "FairHire API Running 🚀"


# ---------------- RUN ----------------
if __name__ == '__main__':
    logger.info(f"Starting server at {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)