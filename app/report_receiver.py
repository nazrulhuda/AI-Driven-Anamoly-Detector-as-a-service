from flask import Flask, request
import os

app = Flask(__name__)

# Directory to store uploaded reports
UPLOAD_FOLDER = '/reports'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Receives file from DDoS detector pod via HTTP POST.
    Example: 'files={'file': open('report.csv','rb')}' in requests.post
    """
    if 'file' not in request.files:
        return "No file part in request", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    print(f"Saved file to {save_path}")
    return f"File {file.filename} uploaded successfully!", 200

if __name__ == '__main__':
    # Listen on port 8000
    app.run(host='0.0.0.0', port=8000)

