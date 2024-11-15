import os
import re
import json
import google.generativeai as genai

genai.configure(api_key="AIzaSyDp_cVjf37RGeF5F19MWs4vuYArJBwqfxo")

def upload_to_gemini(path, mime_type=None):
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  return file

def generativeaifun(imagePath):
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    )

    files = upload_to_gemini(imagePath, mime_type="image/jpeg")

    chat_session = model.start_chat(
    history=[
        {
        "role": "user",
        "parts": [
            files,
            "give me title and description for the image and return response in json format.",
        ],
        },
    ]
    )

    response = chat_session.send_message("INSERT_INPUT_HERE")
    print(response.text)

from flask import Flask, redirect ,request, send_file, send_from_directory, render_template_string, jsonify
from google.cloud import storage

app = Flask(__name__)

os.makedirs('files', exist_ok = True)
bucket_name = 'cndz23737172'

@app.route('/')
def index():
    index_html = """
    <body style="backgorund-color: green">
    <form method="post" enctype="multipart/form-data" action="/upload" method="post">
    <div>
        <label for="file">Choose file to upload</label>
        <input type="file" id="file" name="file" accept="image/jpeg"/>
    </div>
    <div>
        <button>Submit</button>
    </div>
    </form>
    <h3>Uploaded Files:</h3>
    <ul>
    """

    for file in list_files():
        index_html += f"<li><a href='/file/{file}'>{file}</a></li>"

    index_html += "</ul> </body>"
    return render_template_string(index_html)

app.config['UPLOAD_FOLDER'] = 'files'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

image_metadata = {}
def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    return file

def upload_to_bucket(file1, blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file1)

def generate_title_description(file_uri):
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }


    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    files = upload_to_gemini(file_uri, mime_type="image/jpeg")

    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    files,
                    "give me title and description of image",
                ],
            },
        ]
    )


    response = chat_session.send_message("give me title and description of image")
    return response.text

def parse_response(response_text):
    lines = response_text.split("\n")
    title = lines[0].replace("Title:", "").strip() if "Title:" in lines[0] else "Title not available"
    description = lines[1].replace("Description:", "").strip() if len(lines) > 1 and "Description:" in lines[1] else "Description not available"
    return title, description

@app.route('/upload', methods=['POST'])
def upload_file():    
    file = request.files['file']
    filename = file.filename

    local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(local_path)
    response = generate_title_description(local_path)

    try:
        response = response.replace('*', '').strip()
        repsonse = jsonify(response)
        title_match = re.search(r"Title:\s*(.+)", response)
        description_match = re.search(r"Description:\s*(.+)", response, re.DOTALL)
        title = title_match.group(1).strip() if title_match else "No title found"
        description = description_match.group(1).strip() if description_match else "No description found"
        print(title, description)
    except:
        return "No response available"

    local_file_path = os.path.join(os.getcwd()+'/files', os.path.splitext(filename)[0]+'.txt')

    with open(local_file_path, 'w') as lfp:
        lfp.write(f'{title} \n {description}')

    with open(local_file_path, 'rb') as lfp1:
        print(lfp1, os.path.basename(local_file_path))
        upload_to_bucket(lfp1, os.path.basename(local_file_path))

    file.seek(0)
    upload_to_bucket(file, filename)

    return redirect('/')
    
@app.route('/files')
def list_files():
    files = os.listdir("./files")
    jpegs = []
    for file in files:
        if file.lower().endswith(".jpeg") or file.lower().endswith(".jpg"):
            jpegs.append(file)

    return jpegs

@app.route('/files/<filename>')
def serve_image(filename):
    # paths = os.path.join('./files/', filename)
    # print('hjgjhgfgdtsjdtrdhfh',paths)
    return send_from_directory('./files/', filename)

@app.route('/file/<filename>')
def get_file(filename):
    file_name = os.path.splitext(filename)[0] + '.txt'
    title = "No title"
    description = "No description"
    path = os.path.join('./files', file_name)

    if os.path.exists(path):
        with open(path, 'r') as content:
            cont = content.read()
            texts = cont.split("\n")
            title = texts[0]
            description = texts[1]
            print(title, description)

    view_html = '''<body style="background-color: green">
    <h1>{{ title }}</h1>
    <img src="{{ url_for('serve_image', filename=filename) }}" alt="image">
    <p>{{ description }}</p>
    <a href="{{ url_for('index') }}">back</a>
    </body>
    '''

    return render_template_string(view_html, title=title, description=description, filename=filename)


if __name__ == '__main__':
    app.run(debug=True)