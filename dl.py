from flask import Flask, render_template, send_from_directory, send_file, request, jsonify, redirect, url_for, abort
from flask_httpauth import HTTPBasicAuth
import os
import shutil
from werkzeug.utils import secure_filename
from zipfile import ZipFile, ZIP_STORED

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'D:/Download Server/temp'

# Security
"""
auth = HTTPBasicAuth()

# Define the username and password for authentication
USERNAME = 'admin'
PASSWORD = 'cd@12345'

@auth.verify_password
def verify_password(username, password):
    return username == USERNAME and password == PASSWORD"""

# ... (Your existing code)


# Define the directories
directories = {
    'directory1': 'E:/Media/Movies',
    'directory2': 'H:/Shows',
    'directory3': 'E:/Media/Anime',
    'directory4': 'H:/Anime',
    'directory5': 'D:/Documents/Books',
    'directory6': 'D:/Applications',
    'directory7': 'F:/Movies',
    # Add more directories as needed
}

# Define groups of directories to combine
combined_directories = {
    'Movies': ['directory1', 'directory7'],
    'Shows': ['directory2'],
    'Anime': ['directory3', 'directory4'],
    'Books': ['directory5'],
    'Applications': ['directory6'],
    # Add more groups as needed
}

def get_directory_content(directory_path):
    try:
        files_and_subdirectories = os.listdir(directory_path)
        files_and_subdirectories.sort()
    except FileNotFoundError:
        return [], []

    file_list = []
    subdir_list = []

    for item in files_and_subdirectories:
        item_path = os.path.join(directory_path, item)
        if os.path.isfile(item_path):
            file_list.append(item)
        elif os.path.isdir(item_path):
            subdir_list.append(item)

    return file_list, subdir_list

def get_combined_files_and_subdirectories(combined_directory_names):
    all_files = []
    all_subdirs = []

    for combined_directory_name, combined_directory_keys in combined_directories.items():
        if combined_directory_name in combined_directory_names:
            for directory_key in combined_directory_keys:
                directory_path = directories.get(directory_key)
                if directory_path:
                    file_list, subdir_list = get_directory_content(directory_path)
                    all_files.extend([(directory_key, 'file', file) for file in file_list])
                    all_subdirs.extend([(directory_key, 'dir', subdir) for subdir in subdir_list])

    return all_files, all_subdirs

@app.route('/')
#@auth.login_required
def index():
    return render_template('index.html', combined_directories=combined_directories)

@app.route('/list_files', methods=['GET', 'POST'])
def list_files():
    if request.method == 'POST':
        selected_option = request.form.get('options')
        option_directory = combined_directories.get(selected_option)
        directory_path = directories.get(option_directory[0])

        if selected_option in combined_directories:
            combined_directory_names = [selected_option]
            all_files, all_subdirs = get_combined_files_and_subdirectories(combined_directory_names)
            return render_template('file_list.html', selected_directory=selected_option, directory_path=directory_path, items=all_files + all_subdirs)
        else:
            return "Invalid option."

    selected_directory = request.args.get('directory')
    
    if selected_directory:
        directory_path = directories.get(selected_directory)

        if directory_path:
            file_list, subdir_list = get_directory_content(directory_path)
            return render_template('file_list.html', selected_directory=selected_directory, items=[(selected_directory, file) for file in file_list] + [(selected_directory, subdir) for subdir in subdir_list])
        else:
            return "Invalid directory selection."

    return  redirect(url_for('index'))

@app.route('/download/<directory>/<path:subdirectory>/<filename>')
def download_file(directory, subdirectory, filename):
    print(directory)
    directory_path = os.path.normpath(directories.get(directory)).replace('\\','/')
    real_path = os.path.normpath(os.path.join(directory_path,subdirectory)).replace('\\','/')
    print(real_path)

    if directory_path:
        file_path = os.path.normpath(os.path.join(real_path, filename)).replace('\\','/')
        if os.path.isfile(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return abort(404, f"The specified file '{filename}' in '{directory}/{subdirectory}' was not found.")

    else:
        return abort(404, f"The specified directory '{directory}' was not found.")

@app.route('/download/<directory>/<filename>')
def download_file_top_level(directory, filename):
    print(directory)
    directory_path = os.path.normpath(directories.get(directory)).replace('\\','/')

    if directory_path:
        file_path = os.path.normpath(os.path.join(directory_path, filename)).replace('\\','/')
        if os.path.isfile(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return abort(404, f"The specified file '{filename}' in '{directory} was not found.")

    else:
        return abort(404, f"The specified directory '{directory}' was not found.")

@app.route('/list_subdirectory/<path:base_directory>/<path:subdirectory>')
def list_subdirectory(base_directory, subdirectory):
    normalized_subdirectory = os.path.normpath(subdirectory).replace('\\','/')

    # Check if the base_directory is a regular directory
    if base_directory in directories:
        directory_path = os.path.normpath(os.path.join(directories[base_directory], normalized_subdirectory)).replace('\\','/')
        file_list, subdir_list = get_directory_content(directory_path)

        return render_template('subdirectory_list.html', subdir=normalized_subdirectory, file_list=file_list, subdir_list=subdir_list, base_directory=base_directory)

    # Check if the base_directory is a combined directory
    for combined_directory, combined_keys in combined_directories.items():
        if base_directory in combined_keys:
            all_files, all_subdirs = get_combined_files_and_subdirectories([combined_directory])

            return render_template('subdirectory_list.html', subdir=normalized_subdirectory, file_list=all_files, subdir_list=all_subdirs, base_directory=base_directory)

    return "Invalid directory."

@app.route('/download_all/<path:base_directory>/<path:subdirectory>')
def download_all(base_directory, subdirectory):
    normalized_subdirectory = os.path.normpath(subdirectory).replace('\\','/')

    # Check if the base_directory is a regular directory
    if base_directory in directories:
        directory_path = os.path.normpath(os.path.join(directories[base_directory], normalized_subdirectory)).replace('\\','/')
        file_list, subdir_list = get_directory_content(directory_path)
        zip_filename = f"{normalized_subdirectory.replace(os.path.sep, '_').replace(' ', '_').replace('/', '-')}_files.zip"
        zip_filepath = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)).replace('\\','/')
        
        with ZipFile(zip_filepath, 'w', compression=ZIP_STORED) as zipf:
            for file_name in file_list:
                file_path = os.path.join(directory_path, file_name)
                zipf.write(file_path, os.path.relpath(file_path, directory_path))
                
            for subdir_name in subdir_list:
                subdir_path = os.path.join(directory_path, subdir_name)
                for root, _, files in os.walk(subdir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, directory_path))
                        
            # EMPTY FOLDERS ARE NOT DOWNLOADED

        return send_file(zip_filepath, as_attachment=True)

    # Check if the base_directory is a combined directory
    for combined_directory, combined_keys in combined_directories.items():
        print(combined_directory)
        if base_directory in combined_keys:
            _, all_subdirs = get_combined_files_and_subdirectories([combined_directory])

            zip_filename = f"{normalized_subdirectory.replace(os.path.sep, '_').replace(' ', '_').replace('/', '-')}_files.zip"
            zip_filepath = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)).replace('\\','/')
            print(zip_filepath)

            with ZipFile(zip_filepath, 'w', compression=ZIP_STORED) as zipf:
                for _, _, subdir in all_subdirs:
                    subdir_path = os.path.join(directories[subdir], normalized_subdirectory)
                    for root, _, files in os.walk(subdir_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, subdir_path))

            return send_file(zip_filepath, as_attachment=True)

        print(f"Debug: Download request received for {base_directory}/{subdirectory}")


    return "Invalid directory."

def get_file_size(directory, filename):
    '''
    path = os.path.normpath(os.path.join(directory, filename)).replace('\\','/')
    return os.path.getsize(path)
    '''
    path = os.path.normpath(os.path.join(directory, filename)).replace('\\','/')
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        # If it's a directory, recursively calculate the total size of its contents
        total_size = 0
        with os.scandir(path) as entries:
            for entry in entries:
                total_size += get_file_size(path, entry.name)
        return total_size
    else:
        # For other types (symlinks, etc.), return 0
        return 0

@app.route('/request_get_file_size/<directory>/<path:subdirectory>', methods=['GET'])
def request_get_file_size(directory, subdirectory):
    real_directory = directories.get(directory)

    try:
        real_subdirectory = os.path.normpath(os.path.join(real_directory, subdirectory)).replace('\\','/')
        file_list = os.listdir(real_subdirectory)
        file_sizes = {filename: get_file_size(real_subdirectory, filename) for filename in file_list}
        return jsonify(file_sizes)
    except FileNotFoundError:
        abort(404, f"The specified directory '{directory}/{subdirectory}' was not found.")

def get_file_size_top_level(directory, filename):
    '''
    path = os.path.normpath(os.path.join(directory, filename)).replace('\\','/')
    return os.path.getsize(path)
    '''
    path = os.path.normpath(os.path.join(directory, filename)).replace('\\','/')
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        # If it's a directory, recursively calculate the total size of its contents
        total_size = 0
        with os.scandir(path) as entries:
            for entry in entries:
                total_size += get_file_size(path, entry.name)
                print(total_size)
        return total_size
    else:
        # For other types (symlinks, etc.), return 0
        return 0
        
@app.route('/request_get_file_size_top_level/<path:directory>', methods=['GET'])
def request_get_file_size_top_level(directory):
    print("Requested URL:", request.url)
    directory = os.path.normpath(directory).replace('\\','/')

    try:
        file_list = os.listdir(directory)
        file_sizes = {filename: get_file_size_top_level(directory, filename) for filename in file_list}
        return jsonify(file_sizes)
    except FileNotFoundError:
        print("tsk")
        abort(404, f"The specified directory '{directory}' was not found.")

if __name__ == '__main__':
    port = 8880
    app.run(debug=True, port=port, host='::')
