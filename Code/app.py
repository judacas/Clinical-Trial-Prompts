import os
from flask import Flask, render_template, request, jsonify
import analyzer

app = Flask(__name__)

TRIALS_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "Trials")
CHIA_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "CHIA")
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_trials', methods=['GET', 'POST'])
def process_trials():
    if request.method == 'POST':
        trials_folder = os.path.join(TRIALS_FOLDER, request.form['subfolders'], request.form['trials_folder'])
        # Placeholder for processing trials
        print(trials_folder)
        processed_trials = analyzer.processTrialsInFolder(trials_folder)
        return jsonify(result=processed_trials)
    subfolders = [f.name for f in os.scandir(TRIALS_FOLDER) if f.is_dir()]
    return render_template('process_trials.html', subfolders=subfolders)

@app.route('/get_raw_trials', methods=['GET', 'POST'])
def get_raw_trials():
    if request.method == 'POST':
        start_index = int(request.form['start_index'])
        num_trials = int(request.form['num_trials'])
        # Placeholder for fetching raw trials
        fetched_trials = get_raw_trials_backend(start_index, num_trials)
        return jsonify(result=fetched_trials)
    return render_template('get_raw_trials.html')

@app.route('/list_subfolders', methods=['GET'])
def list_subfolders():
    category = str(request.args.get('folder'))
    category_path = os.path.join(TRIALS_FOLDER, category)
    subfolders = [f.name for f in os.scandir(category_path) if f.is_dir()]
    return jsonify(subfolders=subfolders)

@app.route('/list_trials', methods=['GET'])
def list_trials():
    # Placeholder for listing trials
    trials = list_trials_backend()
    return jsonify(trials=trials)

def process_trials_backend(trials_folder):
    pass  # To be implemented

def get_raw_trials_backend(start_index, num_trials):
    pass  # To be implemented

def list_trials_backend():
    pass  # To be implemented

if __name__ == '__main__':
    app.run(debug=True)
