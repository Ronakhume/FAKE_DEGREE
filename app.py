import http.server
import socketserver
import json
import urllib.parse
import os
import hashlib
import secrets
import time
import mimetypes
from pathlib import Path
import sqlite3
import datetime

# Import our modules
from models import db_manager
from ocr_processor import OCRProcessor
from fraud_detector import FraudDetector

# Configuration
PORT = 5000
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# Initialize processors
ocr_processor = OCRProcessor()
fraud_detector = FraudDetector()

def allowed_file(filename):
    """Check if uploaded file is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_hash(filepath):
    """Calculate file hash"""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def read_template(template_name):
    """Read HTML template"""
    try:
        with open(f'templates/{template_name}', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<html><body><h1>Template {template_name} not found</h1></body></html>"

def render_template(template_name, **kwargs):
    """Simple template rendering"""
    template = read_template(template_name)
    
    # Simple replacement for template variables
    for key, value in kwargs.items():
        if isinstance(value, list):
            # Handle list rendering
            if key == 'certificates':
                cert_rows = ''
                for cert in value:
                    fraud_count = cert.get('fraud_reports_count', 0)
                    status = 'Suspicious' if fraud_count > 0 else 'Verified'
                    status_class = 'suspicious' if fraud_count > 0 else 'verified'
                    fraud_score = cert.get('max_fraud_score', 0) * 100 if cert.get('max_fraud_score') else 0
                    
                    cert_rows += f'''
                    <tr>
                        <td><code>{cert.get('certificate_id', 'N/A')}</code></td>
                        <td>{cert.get('student_name', 'N/A')}</td>
                        <td>{cert.get('roll_number', 'N/A')}</td>
                        <td>{cert.get('institution', 'N/A')}</td>
                        <td><span class="status-badge {status_class}"><i class="fas fa-{'check-circle' if status == 'Verified' else 'exclamation-triangle'}"></i> {status}</span></td>
                        <td><div class="fraud-score {'low' if fraud_score == 0 else ''}">{fraud_score:.1f}%</div></td>
                        <td>{cert.get('created_at', 'N/A')}</td>
                        <td><button class="btn-small" onclick="viewCertificate('{cert.get('certificate_id', '')}')"><i class="fas fa-eye"></i> View</button></td>
                    </tr>
                    '''
                template = template.replace('{% for cert in certificates %}...{% endfor %}', cert_rows)
            elif key == 'fraud_reports':
                report_cards = ''
                for report in value:
                    report_cards += f'''
                    <div class="fraud-report-card">
                        <div class="report-header">
                            <div class="report-type">
                                <i class="fas fa-exclamation-triangle"></i>
                                {report.get('fraud_type', '').replace('_', ' ').title()}
                            </div>
                            <div class="report-confidence">
                                {(report.get('confidence_score', 0) * 100):.1f}% confidence
                            </div>
                        </div>
                        <div class="report-details">
                            <div class="report-cert">
                                Certificate: <strong>{report.get('certificate_id', 'N/A')}</strong>
                                {f'| Student: <strong>{report.get("student_name", "")}</strong>' if report.get('student_name') else ''}
                            </div>
                            <div class="report-description">{report.get('description', '')}</div>
                            <div class="report-time">{report.get('detected_at', '')}</div>
                        </div>
                    </div>
                    '''
                template = template.replace('{% for report in fraud_reports %}...{% endfor %}', report_cards)
        else:
            # Handle simple variable replacement
            template = template.replace('{{ ' + key + ' }}', str(value))
            template = template.replace('{{' + key + '}}', str(value))
            
            # Handle stats object specifically for admin template
            if key == 'stats' and isinstance(value, dict):
                template = template.replace('{{ total_certificates }}', str(value.get('total_certificates', 0)))
                template = template.replace('{{ verified_certificates }}', str(value.get('verified_certificates', 0)))
                template = template.replace('{{ suspicious_certificates }}', str(value.get('suspicious_certificates', 0)))
                template = template.replace('{{ fraud_detection_rate }}', f"{value.get('fraud_detection_rate', 0):.1f}")
    
    return template

class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/' or path == '/index':
            self.send_html_response(render_template('index.html'))
        elif path == '/upload':
            self.send_html_response(render_template('upload.html'))
        elif path == '/admin':
            self.handle_admin_dashboard()
        elif path.startswith('/verify/'):
            cert_id = path.split('/')[-1]
            self.handle_verify_certificate(cert_id)
        elif path == '/api/stats':
            self.handle_api_stats()
        elif path.startswith('/static/'):
            self.serve_static_file(path)
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/upload':
            self.handle_upload()
        else:
            self.send_error(404)
    
    def send_html_response(self, html):
        """Send HTML response"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(html.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_json_response(self, data):
        """Send JSON response"""
        json_data = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def serve_static_file(self, path):
        """Serve static files"""
        try:
            # Remove leading slash and serve from current directory
            file_path = path[1:]  # Remove leading /
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'text/plain'
                
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Error serving static file {path}: {e}")
            self.send_error(500)
    
    def handle_admin_dashboard(self):
        """Handle admin dashboard"""
        try:
            certificates = db_manager.get_all_certificates()
            fraud_reports = db_manager.get_fraud_reports()[:20]
            
            total_certificates = len(certificates)
            suspicious_count = sum(1 for cert in certificates if (cert.get('fraud_reports_count', 0)) > 0)
            verified_count = total_certificates - suspicious_count
            fraud_detection_rate = (suspicious_count / total_certificates * 100) if total_certificates > 0 else 0
            
            stats = {
                'total_certificates': total_certificates,
                'verified_certificates': verified_count,
                'suspicious_certificates': suspicious_count,
                'fraud_detection_rate': fraud_detection_rate
            }
            
            html = render_template('admin.html', 
                                certificates=certificates, 
                                fraud_reports=fraud_reports,
                                stats=stats)
            self.send_html_response(html)
            
        except Exception as e:
            print(f"Error in admin dashboard: {e}")
            self.send_error(500)
    
    def handle_verify_certificate(self, cert_id):
        """Handle certificate verification"""
        try:
            certificate = db_manager.get_certificate(cert_id)
            
            if not certificate:
                self.send_json_response({
                    'success': False,
                    'message': 'Certificate not found'
                })
                return
            
            fraud_reports = db_manager.get_fraud_reports(cert_id)
            overall_fraud_score = fraud_detector.calculate_overall_fraud_score(fraud_reports)
            
            self.send_json_response({
                'success': True,
                'certificate': certificate,
                'fraud_reports': fraud_reports,
                'overall_fraud_score': overall_fraud_score,
                'is_suspicious': overall_fraud_score > 0.6,
                'status': 'verified' if overall_fraud_score < 0.3 else 'suspicious' if overall_fraud_score < 0.6 else 'fraudulent'
            })
            
        except Exception as e:
            print(f"Error verifying certificate {cert_id}: {e}")
            self.send_json_response({'error': str(e)})
    
    def handle_api_stats(self):
        """Handle API stats request"""
        try:
            certificates = db_manager.get_all_certificates()
            fraud_reports = db_manager.get_fraud_reports()
            
            total_certificates = len(certificates)
            total_fraud_reports = len(fraud_reports)
            
            fraud_by_type = {}
            for report in fraud_reports:
                fraud_type = report.get('fraud_type', 'unknown')
                fraud_by_type[fraud_type] = fraud_by_type.get(fraud_type, 0) + 1
            
            stats = {
                'total_certificates': total_certificates,
                'total_fraud_reports': total_fraud_reports,
                'fraud_by_type': fraud_by_type,
                'recent_uploads': total_certificates,
            }
            
            self.send_json_response(stats)
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            self.send_json_response({'error': str(e)})
    
    def handle_upload(self):
        """Handle certificate upload"""
        try:
            # This is a simplified upload handler
            # In a real implementation, you'd need proper multipart form parsing
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # For demonstration, we'll simulate processing
            # In reality, you'd parse the multipart form data properly
            
            # Simulate OCR processing with demo data
            cert_data = {
                'certificate_id': f'DEMO-{int(time.time())}',
                'student_name': 'DEMO STUDENT',
                'roll_number': f'DEMO{int(time.time() % 10000)}',
                'marks': 'A (85%)',
                'institution': 'Demo University',
                'course': 'Computer Science',
                'issue_date': 'June 2024',
                'file_hash': hashlib.sha256(post_data).hexdigest(),
                'file_path': f'uploads/demo_{int(time.time())}.jpg'
            }
            
            # Simulate fraud detection
            fraud_reports = [
                {
                    'type': 'demo_check',
                    'confidence': 0.1,
                    'description': 'This is a demo certificate for testing purposes'
                }
            ]
            
            overall_fraud_score = 0.1
            
            # Save to database
            db_manager.add_certificate(cert_data)
            for report in fraud_reports:
                db_manager.add_fraud_report(
                    cert_data['certificate_id'],
                    report['type'],
                    report['confidence'],
                    report['description']
                )
            
            response_data = {
                'success': True,
                'certificate_data': cert_data,
                'extracted_text': 'DEMO CERTIFICATE\\nThis is a demonstration\\nDEMO STUDENT\\nRoll: DEMO1234\\nGrade: A (85%)',
                'fraud_reports': fraud_reports,
                'overall_fraud_score': overall_fraud_score,
                'is_suspicious': overall_fraud_score > 0.6,
                'certificate_saved': True
            }
            
            self.send_json_response(response_data)
            
        except Exception as e:
            print(f"Error handling upload: {e}")
            self.send_json_response({'error': str(e)})

def start_server():
    """Start the HTTP server"""
    try:
        # Initialize database
        db_manager.init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
    
    print(f"Starting Fake Certificate Recognition System...")
    print(f"Server running at: http://localhost:{PORT}")
    
    with socketserver.TCPServer(("", PORT), HTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == '__main__':
    start_server()