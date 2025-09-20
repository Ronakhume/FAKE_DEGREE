import re
import os
import hashlib

class FraudDetector:
    """Fraud detection algorithms for certificates"""
    
    def __init__(self):
        self.pil_available = False
        try:
            from PIL import Image, ImageStat
            self.pil_available = True
            self.Image = Image
        except ImportError:
            print("Warning: PIL/Pillow not available, limited image analysis")
        
        self.fraud_patterns = {
            'invalid_id_format': [
                r'^[A-Z]{2,4}-\d{4}-[A-Z]{2}-\d{3}$',  # Standard format
                r'^CERT-\d{4}-[A-Z]{2,4}-\d{3}$',      # Alternative format
            ],
            'suspicious_text_patterns': [
                r'temporary',
                r'draft',
                r'sample',
                r'copy',
                r'duplicate'
            ]
        }
    
    def analyze_certificate(self, cert_data, image_path, db_manager):
        """Perform comprehensive fraud analysis"""
        fraud_reports = []
        
        # Check for duplicate certificates
        duplicate_check = self._check_duplicates(cert_data, db_manager)
        if duplicate_check['is_fraud']:
            fraud_reports.append(duplicate_check)
        
        # Validate certificate ID format
        id_validation = self._validate_certificate_id(cert_data.get('certificate_id', ''))
        if id_validation['is_fraud']:
            fraud_reports.append(id_validation)
        
        # Check for suspicious text patterns
        text_analysis = self._analyze_text_patterns(cert_data)
        if text_analysis['is_fraud']:
            fraud_reports.append(text_analysis)
        
        # Analyze image properties
        image_analysis = self._analyze_image_properties(image_path)
        if image_analysis['is_fraud']:
            fraud_reports.append(image_analysis)
        
        # Check data consistency
        consistency_check = self._check_data_consistency(cert_data)
        if consistency_check['is_fraud']:
            fraud_reports.append(consistency_check)
        
        return fraud_reports
    
    def _check_duplicates(self, cert_data, db_manager):
        """Check for duplicate certificates"""
        file_hash = cert_data.get('file_hash', '')
        certificate_id = cert_data.get('certificate_id', '')
        
        # Check for exact file duplicates
        duplicate_hash = db_manager.check_duplicate_hash(file_hash)
        if duplicate_hash:
            return {
                'is_fraud': True,
                'type': 'duplicate_file',
                'confidence': 0.95,
                'description': f'Identical file already exists with certificate ID: {duplicate_hash}'
            }
        
        # Check for certificate ID duplicates
        existing_cert = db_manager.get_certificate(certificate_id)
        if existing_cert:
            return {
                'is_fraud': True,
                'type': 'duplicate_id',
                'confidence': 0.90,
                'description': f'Certificate ID {certificate_id} already exists'
            }
        
        return {'is_fraud': False}
    
    def _validate_certificate_id(self, certificate_id):
        """Validate certificate ID format"""
        if not certificate_id:
            return {
                'is_fraud': True,
                'type': 'missing_id',
                'confidence': 0.85,
                'description': 'Certificate ID is missing or empty'
            }
        
        # Check length
        if len(certificate_id) < 5 or len(certificate_id) > 20:
            return {
                'is_fraud': True,
                'type': 'invalid_id_format',
                'confidence': 0.70,
                'description': 'Certificate ID length is suspicious'
            }
        
        # Check for valid format patterns
        valid_format = False
        for pattern in self.fraud_patterns['invalid_id_format']:
            if re.match(pattern, certificate_id):
                valid_format = True
                break
        
        # If it doesn't match any standard format, it might be suspicious
        # But we'll use a lower confidence since institutions might have different formats
        if not valid_format:
            # Check for completely random/suspicious patterns
            if re.match(r'^[a-z]+$', certificate_id) or certificate_id.count('0') > len(certificate_id) * 0.7:
                return {
                    'is_fraud': True,
                    'type': 'suspicious_id_format',
                    'confidence': 0.60,
                    'description': 'Certificate ID format appears suspicious'
                }
        
        return {'is_fraud': False}
    
    def _analyze_text_patterns(self, cert_data):
        """Analyze text for suspicious patterns"""
        text_to_analyze = ' '.join([
            cert_data.get('student_name', ''),
            cert_data.get('institution', ''),
            cert_data.get('course', ''),
            cert_data.get('marks', '')
        ]).lower()
        
        for pattern in self.fraud_patterns['suspicious_text_patterns']:
            if pattern in text_to_analyze:
                return {
                    'is_fraud': True,
                    'type': 'suspicious_text',
                    'confidence': 0.75,
                    'description': f'Found suspicious text pattern: "{pattern}"'
                }
        
        # Check for incomplete/placeholder data
        if any(field in ['', 'n/a', 'na', 'none', 'null'] for field in [
            cert_data.get('student_name', ''),
            cert_data.get('certificate_id', '')
        ]):
            return {
                'is_fraud': True,
                'type': 'incomplete_data',
                'confidence': 0.65,
                'description': 'Certificate contains incomplete or placeholder data'
            }
        
        return {'is_fraud': False}
    
    def _analyze_image_properties(self, image_path):
        """Analyze image properties for signs of tampering"""
        try:
            if self.pil_available:
                return self._analyze_with_pil(image_path)
            else:
                return self._analyze_basic_properties(image_path)
        except Exception as e:
            return {
                'is_fraud': True,
                'type': 'image_analysis_error',
                'confidence': 0.80,
                'description': f'Could not analyze image properties: {str(e)}'
            }
    
    def _analyze_with_pil(self, image_path):
        """Analyze image using PIL"""
        with self.Image.open(image_path) as img:
            # Check image quality/compression
            if hasattr(img, 'info') and 'quality' in img.info:
                quality = img.info['quality']
                if quality < 50:  # Very low quality might indicate multiple saves/edits
                    return {
                        'is_fraud': True,
                        'type': 'low_quality',
                        'confidence': 0.60,
                        'description': f'Image quality is suspiciously low ({quality}%)'
                    }
            
            # Check for unusual dimensions
            width, height = img.size
            aspect_ratio = width / height
            
            # Most certificates have reasonable aspect ratios
            if aspect_ratio < 0.5 or aspect_ratio > 3.0:
                return {
                    'is_fraud': True,
                    'type': 'unusual_dimensions',
                    'confidence': 0.55,
                    'description': f'Unusual aspect ratio: {aspect_ratio:.2f}'
                }
        
        return self._analyze_basic_properties(image_path)
    
    def _analyze_basic_properties(self, image_path):
        """Basic image property analysis"""
        # Check for very small or very large files
        file_size = os.path.getsize(image_path)
        if file_size < 10000:  # Less than 10KB
            return {
                'is_fraud': True,
                'type': 'suspicious_file_size',
                'confidence': 0.70,
                'description': 'File size is suspiciously small'
            }
        elif file_size > 10000000:  # More than 10MB
            return {
                'is_fraud': True,
                'type': 'suspicious_file_size',
                'confidence': 0.50,
                'description': 'File size is unusually large'
            }
        
        return {'is_fraud': False}
    
    def _check_data_consistency(self, cert_data):
        """Check for data consistency issues"""
        student_name = cert_data.get('student_name', '').strip()
        roll_number = cert_data.get('roll_number', '').strip()
        marks = cert_data.get('marks', '').strip()
        
        # Check name format
        if student_name:
            # Names should contain only letters and spaces
            if not re.match(r'^[A-Za-z\s]+$', student_name):
                return {
                    'is_fraud': True,
                    'type': 'invalid_name_format',
                    'confidence': 0.75,
                    'description': 'Student name contains invalid characters'
                }
            
            # Names should not be too short or too long
            if len(student_name) < 2 or len(student_name) > 50:
                return {
                    'is_fraud': True,
                    'type': 'invalid_name_length',
                    'confidence': 0.70,
                    'description': 'Student name length is suspicious'
                }
        
        # Check roll number format
        if roll_number:
            # Should be alphanumeric and reasonable length
            if not re.match(r'^[A-Za-z0-9]+$', roll_number) or len(roll_number) < 3 or len(roll_number) > 15:
                return {
                    'is_fraud': True,
                    'type': 'invalid_roll_format',
                    'confidence': 0.65,
                    'description': 'Roll number format appears invalid'
                }
        
        # Check marks format
        if marks:
            # Should be valid grade or percentage
            if not re.match(r'^[A-F][+-]?|\d+(?:\.\d+)?%?|\d+/\d+|\d+\.\d+$', marks):
                return {
                    'is_fraud': True,
                    'type': 'invalid_marks_format',
                    'confidence': 0.60,
                    'description': 'Marks format appears invalid'
                }
        
        return {'is_fraud': False}
    
    def calculate_overall_fraud_score(self, fraud_reports):
        """Calculate overall fraud probability"""
        if not fraud_reports:
            return 0.0
        
        # Weighted average of confidence scores
        total_weight = 0
        weighted_sum = 0
        
        for report in fraud_reports:
            confidence = report.get('confidence', 0.5)
            weight = self._get_fraud_type_weight(report.get('type', ''))
            
            weighted_sum += confidence * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _get_fraud_type_weight(self, fraud_type):
        """Get weight for different types of fraud"""
        weights = {
            'duplicate_file': 1.0,
            'duplicate_id': 0.9,
            'missing_id': 0.8,
            'invalid_id_format': 0.7,
            'suspicious_text': 0.8,
            'incomplete_data': 0.6,
            'low_quality': 0.5,
            'unusual_dimensions': 0.4,
            'suspicious_file_size': 0.5,
            'invalid_name_format': 0.7,
            'invalid_roll_format': 0.6,
            'invalid_marks_format': 0.5,
        }
        return weights.get(fraud_type, 0.5)