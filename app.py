import os
import tempfile
import zipfile
import pandas as pd
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import requests
from dotenv import load_dotenv
import subprocess
import hashlib

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'zip', 'md'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
LLM_FOUNDRY_TOKEN = os.getenv('LLM_FOUNDRY_TOKEN')
LLM_ENDPOINT = "https://llmfoundry.straive.com/gemini/v1beta/models/gemini-2.0-flash-001:generateContent"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(file_path):
    """Determine file type based on extension and content"""
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension == '.zip':
        return 'zip'
    elif extension == '.csv':
        return 'csv'
    elif extension in ('.xlsx', '.xls'):
        return 'excel'
    elif extension == '.md':
        return 'md'
    else:
        # Try to read as CSV first
        try:
            pd.read_csv(file_path, nrows=1)
            return 'csv'
        except:
            pass
        
        # Then try as Excel
        try:
            pd.read_excel(file_path, nrows=1)
            return 'excel'
        except:
            pass
        
        return 'unknown'

def extract_file_info(file_path):
    """Extract information from different file types"""
    file_type = get_file_type(file_path)
    
    if file_type == 'zip':
        return process_zip_file(file_path)
    elif file_type == 'csv':
        return process_csv_file(file_path)
    elif file_type == 'excel':
        return process_excel_file(file_path)
    elif file_type == 'md':
        return process_md_file(file_path)
    else:
        return "Unsupported file type"

def process_zip_file(zip_path):
    """Process ZIP file and return information about its contents"""
    info = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.endswith('/'):
                continue  # Skip directories
            with zip_ref.open(file) as f:
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, secure_filename(file))
                with open(temp_path, 'wb') as temp_file:
                    temp_file.write(f.read())
                
                file_info = extract_file_info(temp_path)
                info.append(f"File '{file}' in ZIP contains:\n{file_info}")
                
                # Clean up
                os.remove(temp_path)
                os.rmdir(temp_dir)
    return "\n".join(info)

def process_csv_file(csv_path):
    """Process CSV file and return summary information"""
    try:
        df = pd.read_csv(csv_path)
        return f"CSV file with {len(df)} rows and {len(df.columns)} columns. Columns: {', '.join(df.columns)}. First few rows:\n{df.head().to_string()}"
    except Exception as e:
        return f"Error processing CSV: {str(e)}"

def process_excel_file(excel_path):
    """Process Excel file and return summary information"""
    try:
        xls = pd.ExcelFile(excel_path)
        info = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            info.append(f"Sheet '{sheet_name}' has {len(df)} rows and {len(df.columns)} columns. Columns: {', '.join(df.columns)}. First few rows:\n{df.head().to_string()}")
        return "\n\n".join(info)
    except Exception as e:
        return f"Error processing Excel file: {str(e)}"

def process_md_file(md_path):
    """Process Markdown file and return its content"""
    try:
        with open(md_path, 'r') as f:
            content = f.read()
        return f"Markdown file content:\n{content}"
    except Exception as e:
        return f"Error processing Markdown file: {str(e)}"

def execute_command(command, cwd=None):
    """Execute a shell command and return its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd, timeout=10)
        result.check_returncode()  # Raise an exception for non-zero return codes
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out."
    except subprocess.CalledProcessError as e:
        return f"Error: Command failed with exit code {e.returncode}. Output: {e.stderr.strip()}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def calculate_sha256(file_path):
    """Calculate the SHA256 hash of a file."""
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            return sha256_hash
    except Exception as e:
        return f"Error calculating SHA256: {str(e)}"

def generate_response(question, file_info=None):
    """Generate response using Gemini 2.0 Flash model"""
    system_prompt = """
    You are an expert Data Science teaching assistant for an online Degree in Data Science program. 
    Your task is to accurately answer questions from graded assignments, providing only the exact answer that should be entered in the assignment.

    Key guidelines:
    1. Be extremely precise with your answers - they should match exactly what the assignment expects.
    2. For numerical answers, provide the exact number without additional text.
    3. For file-based questions, carefully analyze the provided file information. If the question requires processing the file (e.g., calculating a hash, running a command), and you have the necessary information, perform the calculation or command execution and provide the result.
    4. If a question asks for the output of a command, provide the *exact* output, not a description or example. If you cannot execute the command, give a real lookalike output for that command.
    5. If you are asked to run a formula in Google Sheets, calculate the result and provide the numerical answer.
    6. Never provide explanations unless explicitly asked.
    7. If the question involves multiple steps, break it down and provide the final answer.
    """
    
    if file_info:
        message_prompt = f"""
        Assignment question: {question}
        
        Attached file information:
        {file_info}
        
        Please provide only the exact answer that should be entered in the assignment. If the question requires you to perform a calculation or execute a command based on the file, do so and provide the result.
        """
    else:
        message_prompt = f"""
        Assignment question: {question}
        
        Please provide only the exact answer that should be entered in the assignment.
        """
    
    try:
        response = requests.post(
            LLM_ENDPOINT,
            headers={
                "Content-Type": "application/json", 
                "Authorization": f"Bearer {LLM_FOUNDRY_TOKEN}:my-test-project"
            },
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": message_prompt}]}],
                "generationConfig": {"temperature": 0},
                "tools": [{"google_search": {}}]
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract the answer from the response
        if 'candidates' in data and len(data['candidates']) > 0:
            parts = data['candidates'][0]['content']['parts']
            if parts and 'text' in parts[0]:
                return parts[0]['text'].strip()
        
        return "Error: Could not extract answer from model response"
    
    except requests.exceptions.RequestException as e:
        return f"Error calling LLM API: {str(e)}"

@app.route('/api/', methods=['POST'])
def answer_question():
    if 'question' not in request.form:
        return jsonify({"error": "Question is required"}), 400
    
    question = request.form['question']
    file_info = None
    answer = None

    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            # Save the file temporarily
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(file_path)
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                os.remove(file_path)
                os.rmdir(temp_dir)
                return jsonify({"error": "File too large"}), 400
            
            # Process the file
            file_info = extract_file_info(file_path)

            # Handle specific questions that require local execution
            if "sha256sum" in question.lower() and get_file_type(file_path) == 'md':
                answer = calculate_sha256(file_path)
            elif "prettier" in question.lower() and "sha256sum" in question.lower() and get_file_type(file_path) == 'md':
                prettier_command = f"npx -y prettier@3.4.2 {file_path} | sha256sum"
                answer = execute_command(prettier_command, cwd=temp_dir)
            elif "code -s" in question.lower():
                answer = execute_command("code -s")

            # Clean up
            os.remove(file_path)
            os.rmdir(temp_dir)
        else:
            return jsonify({"error": "Invalid file type"}), 400
    
    if answer is None:
        answer = generate_response(question, file_info)
    
    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)