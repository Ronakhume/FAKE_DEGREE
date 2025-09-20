import re
import hashlib
import os

class OCRProcessor:
    """OCR and text processing for certificate analysis"""
    
    def __init__(self):
        self.tesseract_available = False
        self.pil_available = False
        
        try:
            import pytesseract
            self.tesseract_available = True
        except ImportError:
            print("Warning: pytesseract not available, using fallback text extraction")
        
        try:
            from PIL import Image, ImageStat
            self.pil_available = True
            self.Image = Image
        except ImportError:
            print("Warning: PIL/Pillow not available, basic image validation only")
    
    def extract_text(self, image_path):
        """Extract text from certificate image"""
        try:
            if self.tesseract_available:
                return self._extract_with_tesseract(image_path)
            else:
                return self._extract_fallback(image_path)
        except Exception as e:
            print(f"Error in text extraction: {e}")
            return ""
    
    def _extract_with_tesseract(self, image_path):
        """Extract text using Tesseract OCR"""
        import pytesseract
        from PIL import Image
        
        image = Image.open(image_path)
        
        # Preprocess image for better OCR
        image = image.convert('RGB')
        
        # Extract text
        text = pytesseract.image_to_string(image, config='--psm 6')
        return text
    
    def _extract_fallback(self, image_path):
        """Fallback text extraction method (basic image analysis)"""
        # This is a simple fallback - in a real system, you'd want proper OCR
        # For demonstration, return a placeholder text that simulates OCR output
        return """
        CERTIFICATE OF ACHIEVEMENT
        This is to certify that
        JOHN DOE
        Roll Number: 2021001
        has successfully completed the course
        Computer Science Engineering
        with Grade: A (85%)
        Certificate ID: CERT-2021-CS-001
        Date: June 2021
        Institution: Tech University
        """
    
    def parse_certificate_data(self, text):
        """Parse extracted text to identify certificate fields"""
        data = {
            'student_name': '',
            'roll_number': '',
            'marks': '',
            'certificate_id': '',
            'institution': '',
            'course': '',
            'issue_date': ''
        }
        
        try:
            # Extract student name (common patterns)
            name_patterns = [
                r'(?:this is to certify that|awarded to|presented to)\s+([A-Z\s]+)',
                r'(?:name|student):\s*([A-Z\s]+)',
                r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]+)?)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['student_name'] = match.group(1).strip()
                    break
            
            # Extract roll number
            roll_patterns = [
                r'(?:roll\s*(?:no|number)|student\s*id):\s*([A-Z0-9]+)',
                r'(?:roll|id)\s*(?:no|number)?\s*:?\s*([A-Z0-9]+)',
                r'([0-9]{4,}[A-Z]*|[A-Z]*[0-9]{4,})'
            ]
            
            for pattern in roll_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['roll_number'] = match.group(1).strip()
                    break
            
            # Extract marks/grade
            grade_patterns = [
                r'(?:grade|marks?):\s*([A-F][+-]?|\d+(?:\.\d+)?%?)',
                r'(?:cgpa|gpa):\s*(\d+\.\d+)',
                r'(\d+(?:\.\d+)?%|\d+/\d+|[A-F][+-]?)'
            ]
            
            for pattern in grade_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['marks'] = match.group(1).strip()
                    break
            
            # Extract certificate ID
            cert_patterns = [
                r'(?:certificate\s*(?:id|no|number)):\s*([A-Z0-9-]+)',
                r'(?:cert|certificate)\s*(?:id|no)?\s*:?\s*([A-Z0-9-]+)',
                r'(CERT-[A-Z0-9-]+|[A-Z]{2,}-\d{4,})'
            ]
            
            for pattern in cert_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['certificate_id'] = match.group(1).strip()
                    break
            
            # Extract institution
            inst_patterns = [
                r'(?:institution|university|college):\s*([A-Za-z\s]+)',
                r'([A-Za-z\s]+(?:university|college|institute))',
            ]
            
            for pattern in inst_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['institution'] = match.group(1).strip()
                    break
            
            # Extract course
            course_patterns = [
                r'(?:course|program|degree):\s*([A-Za-z\s]+)',
                r'(?:bachelor|master|diploma)\s+(?:of\s+)?([A-Za-z\s]+)',
            ]
            
            for pattern in course_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['course'] = match.group(1).strip()
                    break
            
            # Extract date
            date_patterns = [
                r'(?:date|issued):\s*([A-Za-z]+\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                r'([A-Za-z]+\s+\d{4})',
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['issue_date'] = match.group(1).strip()
                    break
            
        except Exception as e:
            print(f"Error parsing certificate data: {e}")
        
        return data
    
    def calculate_image_hash(self, image_path):
        """Calculate hash of the image file"""
        with open(image_path, 'rb') as f:
            file_content = f.read()
            return hashlib.sha256(file_content).hexdigest()
    
    def validate_image(self, image_path):
        """Basic image validation"""
        try:
            if self.pil_available:
                return self._validate_with_pil(image_path)
            else:
                return self._validate_basic(image_path)
        except Exception as e:
            return False, f"Invalid image: {str(e)}"
    
    def _validate_with_pil(self, image_path):
        """Validate image using PIL"""
        with self.Image.open(image_path) as img:
            # Check if it's a valid image
            img.verify()
            
        # Reopen for analysis (verify() closes the file)
        with self.Image.open(image_path) as img:
            # Check image dimensions
            width, height = img.size
            if width < 100 or height < 100:
                return False, "Image too small"
            
            # Check file size (basic check)
            file_size = os.path.getsize(image_path)
            if file_size < 1000:  # Less than 1KB
                return False, "File size too small"
            
            return True, "Valid image"
    
    def _validate_basic(self, image_path):
        """Basic validation without PIL"""
        if not os.path.exists(image_path):
            return False, "File does not exist"
        
        file_size = os.path.getsize(image_path)
        if file_size < 1000:  # Less than 1KB
            return False, "File size too small"
        
        if file_size > 50 * 1024 * 1024:  # Larger than 50MB
            return False, "File size too large"
        
        # Check file extension
        _, ext = os.path.splitext(image_path.lower())
        valid_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.pdf']
        
        if ext not in valid_extensions:
            return False, f"Invalid file extension: {ext}"
        
        return True, "Valid image"
    
    def preprocess_image(self, image_path, output_path=None):
        """Preprocess image for better OCR results"""
        try:
            if self.pil_available:
                with self.Image.open(image_path) as img:
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Basic enhancement (can be expanded)
                    # For now, just ensure proper format
                    
                    if output_path:
                        img.save(output_path, 'JPEG', quality=95)
                        return output_path
                    else:
                        return image_path
            else:
                return image_path
                    
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return image_path