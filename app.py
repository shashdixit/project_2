from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
import zipfile
import pandas as pd
from utils.answer_generator import generate_answer

app = Flask(__name__)

@app.route('/api/', methods=['POST'])
def answer_question():
    # Get the question from the request
    question = request.form.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    # Check if there are any file attachments
    files = {}
    if 'file' in request.files:
        file = request.files['file']
        if file.filename:
            # Create a temporary directory to store the file
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(file_path)
            
            # If it's a zip file, extract it
            if file.filename.endswith('.zip'):
                extract_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Check for CSV files in the extracted directory
                for root, _, filenames in os.walk(extract_dir):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            csv_path = os.path.join(root, filename)
                            try:
                                df = pd.read_csv(csv_path)
                                if 'answer' in df.columns:
                                    files['csv_answer'] = df['answer'].iloc[0]
                            except Exception as e:
                                print(f"Error reading CSV: {e}")
            
            files['original_file'] = file_path
    
    # Generate the answer based on the question and files
    answer = generate_answer(question, files)
    
    # Clean up temporary files if needed
    # (In a production environment, you might want to use a more robust cleanup mechanism)
    
    return jsonify({"answer": answer})

@app.route('/', methods=['GET'])
def home():
    return "API is running. Send POST requests to /api/ endpoint."

if __name__ == '__main__':
    app.run(debug=True)