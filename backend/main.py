from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import json
import tempfile
from datetime import datetime
import uuid
import logging
from pathlib import Path
import traceback
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Ensure required directories exist first (before logging setup)
os.makedirs('resumes', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Import your custom modules
from resume_extractor_cl import process_resume_file
from resume_summarizer import resume_job_match_analysis, generate_hiring_report
from config import FIREBASE_STORAGE_BUCKET, DEBUG, MAX_CONTENT_LENGTH, is_allowed_file

# Configure logging (after creating directories)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configure Flask settings
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = 'resumes'

# Initialize Firebase Admin SDK
try:
    # Check if Firebase is already initialized
    if not firebase_admin._apps:
        # Try to use service account key file
        if os.path.exists('serviceAccountKey.json'):
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred, {
                'storageBucket': FIREBASE_STORAGE_BUCKET
            })
            logger.info("Firebase initialized with service account key")
        else:
            # Fallback to environment variables
            from config import FIREBASE_CONFIG
            cred = credentials.Certificate(FIREBASE_CONFIG)
            firebase_admin.initialize_app(cred, {
                'storageBucket': FIREBASE_STORAGE_BUCKET
            })
            logger.info("Firebase initialized with environment config")
    
    # Initialize Firestore and Storage
    db = firestore.client()
    bucket = storage.bucket()
    logger.info("Firebase services initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    db = None
    bucket = None

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": "File too large. Maximum size allowed is 16MB.",
        "max_size": "16MB"
    }), 413

@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        "error": "Bad request. Please check your input data.",
        "details": str(e)
    }), 400

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({
        "error": "Internal server error. Please try again later.",
        "message": "An unexpected error occurred while processing your request."
    }), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service status"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "flask": "running",
                "firebase": "connected" if db and bucket else "disconnected",
                "storage": "available" if os.path.exists('resumes') else "unavailable"
            }
        }
        
        # Test Firebase connection
        if db:
            try:
                # Try to read from Firestore
                test_ref = db.collection('health_check').limit(1)
                list(test_ref.stream())
                health_status["services"]["firestore"] = "connected"
            except Exception as e:
                health_status["services"]["firestore"] = f"error: {str(e)}"
        
        return jsonify(health_status), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

# Main resume upload and processing endpoint
@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """
    Upload and process a resume PDF file with optional job description
    """
    temp_file_path = None
    session_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Starting resume upload for session: {session_id}")
        
        # Validate Firebase connection
        if not db or not bucket:
            return jsonify({
                "error": "Firebase service unavailable. Please check server configuration.",
                "session_id": session_id
            }), 503
        
        # Check if file is present in request
        if 'resume' not in request.files:
            return jsonify({
                "error": "No resume file provided. Please select a PDF file.",
                "session_id": session_id
            }), 400
        
        file = request.files['resume']
        job_description = request.form.get('job_description', '').strip()
        
        # Validate file selection
        if file.filename == '':
            return jsonify({
                "error": "No file selected. Please choose a resume PDF file.",
                "session_id": session_id
            }), 400
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                "error": "Invalid file type. Only PDF files are allowed.",
                "accepted_formats": [".pdf"],
                "session_id": session_id
            }), 400
        
        # Validate file size (already handled by Flask config, but double-check)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_CONTENT_LENGTH:
            return jsonify({
                "error": f"File too large. Maximum size allowed is {MAX_CONTENT_LENGTH // (1024*1024)}MB.",
                "file_size": f"{file_size // (1024*1024)}MB",
                "session_id": session_id
            }), 413
        
        # Secure filename
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"resume_{session_id}.pdf"
        
        timestamp = datetime.now().isoformat()
        
        # Create temporary file to store uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix=f'resume_{session_id}_') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        logger.info(f"File saved temporarily: {temp_file_path}")
        
        # Initialize processing status in Firestore
        processing_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "filename": filename,
            "job_description": job_description,
            "file_size": file_size,
            "processing_status": "processing",
            "progress": {
                "step": "initializing",
                "message": "Starting resume processing..."
            }
        }
        
        doc_ref = db.collection('resumes').document(session_id)
        doc_ref.set(processing_data)
        
        logger.info(f"Processing resume for session: {session_id}")
        
        # Update progress
        doc_ref.update({
            "progress.step": "extracting",
            "progress.message": "Extracting text and analyzing resume..."
        })
        
        # Process the resume using your existing function
        extracted_data, questions, summary = process_resume_file(temp_file_path, job_description)
        
        # Check if extraction was successful
        if isinstance(extracted_data, dict) and 'error' in extracted_data:
            error_msg = extracted_data['error']
            logger.error(f"Resume extraction failed: {error_msg}")
            
            # Update Firestore with error
            doc_ref.update({
                "processing_status": "failed",
                "error": error_msg,
                "progress.step": "failed",
                "progress.message": f"Processing failed: {error_msg}"
            })
            
            return jsonify({
                "success": False,
                "error": error_msg,
                "session_id": session_id,
                "details": "Resume processing failed during text extraction or analysis."
            }), 500
        
        # Update progress
        doc_ref.update({
            "progress.step": "storing",
            "progress.message": "Saving processed data..."
        })
        
        # Upload original PDF to Firebase Storage
        try:
            blob = bucket.blob(f"resumes/{session_id}/{filename}")
            blob.upload_from_filename(temp_file_path)
            blob.make_public()
            file_url = blob.public_url
            logger.info(f"File uploaded to Firebase Storage: {file_url}")
        except Exception as storage_error:
            logger.warning(f"Failed to upload to Firebase Storage: {storage_error}")
            file_url = None
        
        # Prepare comprehensive data for Firebase storage
        resume_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "filename": filename,
            "file_size": file_size,
            "file_url": file_url,
            "job_description": job_description,
            "extracted_data": extracted_data,
            "interview_questions": questions,
            "job_match_summary": summary,
            "processing_status": "completed",
            "progress": {
                "step": "completed",
                "message": "Resume processing completed successfully"
            },
            "metadata": {
                "processing_time": datetime.now().isoformat(),
                "candidate_name": extracted_data.get('personal_information', {}).get('name', 'Unknown') if extracted_data else 'Unknown',
                "has_job_match": bool(summary and 'error' not in summary),
                "match_score": summary.get('match_score') if summary and 'error' not in summary else None
            }
        }
        
        # Store final data in Firestore
        doc_ref.set(resume_data)
        logger.info(f"Resume processing completed for session: {session_id}")
        
        # Prepare response data
        response_data = {
            "extracted_data": extracted_data,
            "interview_questions": questions,
            "job_match_summary": summary
        }
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Resume processed successfully!",
            "data": response_data,
            "metadata": {
                "filename": filename,
                "file_size": file_size,
                "processing_time": datetime.now().isoformat(),
                "has_job_match": bool(summary and 'error' not in summary)
            }
        }), 200
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error(f"Error processing resume: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update Firestore with error if possible
        try:
            if db:
                doc_ref = db.collection('resumes').document(session_id)
                doc_ref.update({
                    "processing_status": "failed",
                    "error": error_msg,
                    "progress.step": "failed",
                    "progress.message": f"Processing failed: {error_msg}"
                })
        except:
            pass
        
        return jsonify({
            "success": False,
            "error": error_msg,
            "session_id": session_id,
            "details": "An unexpected error occurred during resume processing."
        }), 500
        
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {cleanup_error}")

# Get resume data by session ID
@app.route('/get-resume/<session_id>', methods=['GET'])
def get_resume(session_id):
    """
    Retrieve processed resume data by session ID
    """
    try:
        if not db:
            return jsonify({"error": "Database service unavailable"}), 503
        
        doc_ref = db.collection('resumes').document(session_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            logger.info(f"Retrieved resume data for session: {session_id}")
            return jsonify({
                "success": True,
                "session_id": session_id,
                "data": data
            }), 200
        else:
            logger.warning(f"Resume not found for session: {session_id}")
            return jsonify({
                "success": False,
                "error": "Resume not found",
                "session_id": session_id
            }), 404
            
    except Exception as e:
        logger.error(f"Error retrieving resume {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Retrieval failed: {str(e)}",
            "session_id": session_id
        }), 500

# List all processed resumes
@app.route('/list-resumes', methods=['GET'])
def list_resumes():
    """
    List all processed resumes with optional filtering and pagination
    """
    try:
        if not db:
            return jsonify({"error": "Database service unavailable"}), 503
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 per request
        status_filter = request.args.get('status')  # completed, processing, failed
        sort_by = request.args.get('sort_by', 'timestamp')  # timestamp, match_score
        sort_order = request.args.get('sort_order', 'desc')  # asc, desc
        
        # Build query
        query = db.collection('resumes')
        
        # Apply status filter
        if status_filter:
            query = query.where('processing_status', '==', status_filter)
        
        # Apply sorting
        direction = firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING
        
        if sort_by == 'match_score':
            query = query.order_by('metadata.match_score', direction=direction)
        else:
            query = query.order_by('timestamp', direction=direction)
        
        # Apply limit
        query = query.limit(limit)
        
        docs = query.stream()
        
        resumes = []
        for doc in docs:
            resume_data = doc.to_dict()
            # Return only summary info for listing
            resumes.append({
                "session_id": resume_data.get('session_id'),
                "timestamp": resume_data.get('timestamp'),
                "filename": resume_data.get('filename'),
                "processing_status": resume_data.get('processing_status'),
                "candidate_name": resume_data.get('metadata', {}).get('candidate_name', 'Unknown'),
                "match_score": resume_data.get('metadata', {}).get('match_score'),
                "has_job_match": resume_data.get('metadata', {}).get('has_job_match', False),
                "file_size": resume_data.get('file_size')
            })
        
        logger.info(f"Listed {len(resumes)} resumes")
        return jsonify({
            "success": True,
            "resumes": resumes,
            "count": len(resumes),
            "filters": {
                "status": status_filter,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "limit": limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing resumes: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Listing failed: {str(e)}"
        }), 500

# Delete resume and associated files
@app.route('/delete-resume/<session_id>', methods=['DELETE'])
def delete_resume(session_id):
    """
    Delete a processed resume and its associated files
    """
    try:
        if not db or not bucket:
            return jsonify({"error": "Firebase services unavailable"}), 503
        
        # Check if resume exists
        doc_ref = db.collection('resumes').document(session_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({
                "success": False,
                "error": "Resume not found",
                "session_id": session_id
            }), 404
        
        # Delete from Firestore
        doc_ref.delete()
        logger.info(f"Deleted resume document: {session_id}")
        
        # Delete from Firebase Storage
        try:
            blobs = bucket.list_blobs(prefix=f"resumes/{session_id}/")
            deleted_files = []
            for blob in blobs:
                blob.delete()
                deleted_files.append(blob.name)
            logger.info(f"Deleted {len(deleted_files)} files from storage")
        except Exception as storage_error:
            logger.warning(f"Error deleting storage files: {storage_error}")
        
        return jsonify({
            "success": True,
            "message": "Resume deleted successfully",
            "session_id": session_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting resume {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Deletion failed: {str(e)}",
            "session_id": session_id
        }), 500

# Get processing status
@app.route('/status/<session_id>', methods=['GET'])
def get_processing_status(session_id):
    """
    Get the current processing status of a resume
    """
    try:
        if not db:
            return jsonify({"error": "Database service unavailable"}), 503
        
        doc_ref = db.collection('resumes').document(session_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            status_info = {
                "session_id": session_id,
                "processing_status": data.get('processing_status', 'unknown'),
                "progress": data.get('progress', {}),
                "timestamp": data.get('timestamp'),
                "error": data.get('error')
            }
            return jsonify({
                "success": True,
                "status": status_info
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Session not found",
                "session_id": session_id
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting status for {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Status check failed: {str(e)}",
            "session_id": session_id
        }), 500

# Generate hiring report
@app.route('/generate-report/<session_id>', methods=['POST'])
def generate_report(session_id):
    """
    Generate a comprehensive hiring report for a processed resume
    """
    try:
        if not db:
            return jsonify({"error": "Database service unavailable"}), 503
        
        # Get resume data
        doc_ref = db.collection('resumes').document(session_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({
                "success": False,
                "error": "Resume not found",
                "session_id": session_id
            }), 404
        
        resume_data = doc.to_dict()
        job_match_summary = resume_data.get('job_match_summary')
        
        if not job_match_summary or 'error' in job_match_summary:
            return jsonify({
                "success": False,
                "error": "No job match analysis available for report generation",
                "session_id": session_id
            }), 400
        
        # Get job title from request or use default
        request_data = request.get_json() or {}
        job_title = request_data.get('job_title', 'Position')
        
        # Generate report
        report = generate_hiring_report(job_match_summary, job_title)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "report": report,
            "job_title": job_title,
            "generated_at": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating report for {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Report generation failed: {str(e)}",
            "session_id": session_id
        }), 500

# Batch upload endpoint (bonus feature)
@app.route('/batch-upload', methods=['POST'])
def batch_upload():
    """
    Upload and process multiple resumes against a single job description
    """
    try:
        if not db or not bucket:
            return jsonify({"error": "Firebase services unavailable"}), 503
        
        # Get job description
        job_description = request.form.get('job_description', '').strip()
        if not job_description:
            return jsonify({
                "error": "Job description is required for batch processing"
            }), 400
        
        # Get uploaded files
        uploaded_files = request.files.getlist('resumes')
        if not uploaded_files:
            return jsonify({
                "error": "No resume files provided"
            }), 400
        
        batch_id = str(uuid.uuid4())
        results = []
        
        for file in uploaded_files:
            if file.filename and file.filename.endswith('.pdf'):
                try:
                    # Process each file individually
                    # This is a simplified version - you might want to optimize this
                    session_id = str(uuid.uuid4())
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                        file.save(temp_file.name)
                        extracted_data, questions, summary = process_resume_file(temp_file.name, job_description)
                        os.unlink(temp_file.name)
                    
                    if not isinstance(extracted_data, dict) or 'error' not in extracted_data:
                        results.append({
                            "session_id": session_id,
                            "filename": file.filename,
                            "status": "success",
                            "match_score": summary.get('match_score') if summary else None,
                            "candidate_name": extracted_data.get('personal_information', {}).get('name', 'Unknown')
                        })
                    else:
                        results.append({
                            "session_id": session_id,
                            "filename": file.filename,
                            "status": "failed",
                            "error": extracted_data.get('error')
                        })
                        
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "status": "failed",
                        "error": str(e)
                    })
        
        # Sort by match score
        successful_results = [r for r in results if r.get('status') == 'success' and r.get('match_score')]
        successful_results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "total_files": len(uploaded_files),
            "processed": len(results),
            "successful": len(successful_results),
            "failed": len([r for r in results if r.get('status') == 'failed']),
            "results": results,
            "top_candidates": successful_results[:5]
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Batch processing failed: {str(e)}"
        }), 500

# CORS preflight handler
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'message': 'OK'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

# Application entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = DEBUG
    
    logger.info(f"Starting Resume Processor API on port {port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Firebase initialized: {db is not None and bucket is not None}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        threaded=True
    )