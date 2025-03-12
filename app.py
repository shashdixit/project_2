from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
import zipfile
import pandas as pd
import subprocess, hashlib
from utils.answer_generator import generate_answer

app = Flask(__name__)

# def answer_question():
# # Get the question from the request
# question = request.form.get('question')
# if not question:
#     return jsonify({"error": "No question provided"}), 400

# # Create a temporary directory for file operations
# temp_dir = tempfile.mkdtemp()

# try:
#     # Check if there are any file attachments
#     if 'file' in request.files:
#         file = request.files['file']
#         if file.filename:
#             file_path = os.path.join(temp_dir, secure_filename(file.filename))
#             file.save(file_path)
            
#             # Special handling for the npx prettier question
#             if "npx" in question.lower() and "prettier" in question.lower() and "sha256sum" in question.lower():
#                 # Save the file as README.md
#                 readme_path = os.path.join(temp_dir, "README.md")
#                 with open(file_path, 'rb') as src_file:
#                     with open(readme_path, 'wb') as dest_file:
#                         dest_file.write(src_file.read())
                
#                 try:
#                     # Run the npx prettier command
#                     prettier_process = subprocess.run(
#                         ["npx.cmd", "-y", "prettier@3.4.2", "README.md"], 
#                         capture_output=True,
#                         text=True,
#                         cwd=temp_dir
#                     )
                    
#                     # Get the output and calculate SHA256 hash
#                     prettier_output = prettier_process.stdout.encode('utf-8')
#                     sha256_hash = hashlib.sha256(prettier_output).hexdigest()
                    
#                     # Return the hash with trailing spaces (as sha256sum would)
#                     return jsonify({"answer": f"{sha256_hash}"})
#                 except Exception as e:
#                     return jsonify({"answer": f"Error running command: {str(e)}"})
            
#             # If it's a zip file, extract it
#             if file.filename.endswith('.zip'):
#                 extract_dir = os.path.join(temp_dir, 'extracted')
#                 os.makedirs(extract_dir, exist_ok=True)
#                 with zipfile.ZipFile(file_path, 'r') as zip_ref:
#                     zip_ref.extractall(extract_dir)
                
#                 # Check for CSV files in the extracted directory
#                 for root, _, filenames in os.walk(extract_dir):
#                     for filename in filenames:
#                         if filename.endswith('.csv'):
#                             csv_path = os.path.join(root, filename)
#                             try:
#                                 df = pd.read_csv(csv_path)
#                                 if 'answer' in df.columns:
#                                     return jsonify({"answer": str(df['answer'].iloc[0])})
#                             except Exception as e:
#                                 return jsonify({"answer": f"Error reading CSV: {str(e)}"})
    
#         # Generate the answer based on the question and files
#         answer = generate_answer(question, file)
        
#         return jsonify({"answer": answer})

# finally:
#     # Clean up temporary files
#     try:
#         shutil.rmtree(temp_dir)
#     except Exception:
#         pass

@app.route('/api/', methods=['POST'])
def answer_question():
    # Get the question from the request
    question = request.form.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    # Check if there are any file attachments
    temp_dir = tempfile.mkdtemp()
    files = {}
    try:
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                # Create a temporary directory to store the file
                file_path = os.path.join(temp_dir, secure_filename(file.filename))
                file.save(file_path)

                # Special handling for the npx prettier question
                if "npx" in question.lower() and "prettier" in question.lower() and "sha256sum" in question.lower():
                    # Save the file as README.md
                    readme_path = os.path.join(temp_dir, "README.md")
                    with open(file_path, 'rb') as src_file:
                        with open(readme_path, 'wb') as dest_file:
                            dest_file.write(src_file.read())
                    
                    try:
                        # Run the npx prettier command
                        prettier_process = subprocess.run(
                            ["npx.cmd", "-y", "prettier@3.4.2", "README.md"], 
                            capture_output=True,
                            text=True,
                            cwd=temp_dir
                        )
                        
                        # Get the output and calculate SHA256 hash
                        prettier_output = prettier_process.stdout.encode('utf-8')
                        sha256_hash = hashlib.sha256(prettier_output).hexdigest()
                        
                        # Return the hash with trailing spaces (as sha256sum would)
                        return jsonify({"answer": f"{sha256_hash}"})
                    except Exception as e:
                        return jsonify({"answer": f"Error running command: {str(e)}"})
                
                # # If it's a zip file, extract it
                # if file.filename.endswith('.zip'):
                #     extract_dir = os.path.join(temp_dir, 'extracted')
                #     os.makedirs(extract_dir, exist_ok=True)
                #     with zipfile.ZipFile(file_path, 'r') as zip_ref:
                #         zip_ref.extractall(extract_dir)
                    
                #     # Check for CSV files in the extracted directory
                #     for root, _, filenames in os.walk(extract_dir):
                #         for filename in filenames:
                #             if filename.endswith('.csv'):
                #                 csv_path = os.path.join(root, filename)
                #                 try:
                #                     df = pd.read_csv(csv_path)
                #                     if 'answer' in df.columns:
                #                         files['csv_answer'] = df['answer'].iloc[0]
                #                 except Exception as e:
                #                     print(f"Error reading CSV: {e}")
                
                # files['original_file'] = file_path
        
        # Generate the answer based on the question and files
        answer = generate_answer(question, files)
        
        # Clean up temporary files if needed
        # (In a production environment, you might want to use a more robust cleanup mechanism)
        
        return jsonify({"answer": answer})
    
    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

@app.route('/', methods=['GET'])
def home():
    return "API is running. Send POST requests to /api/ endpoint."

if __name__ == '__main__':
    app.run(debug=True)