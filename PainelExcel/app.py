import os
from flask import Flask, request, redirect, url_for, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data')
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}
DATA_FILE = os.path.join(UPLOAD_FOLDER, 'data.csv')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return {'error': 'no file part'}, 400
    file = request.files['file']
    if file.filename == '':
        return {'error': 'no selected file'}, 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(dest)
        # try to parse to a consistent CSV for the dashboard
        try:
            import pandas as pd
        except Exception as e:
            return {'error': f'pandas required: {e}'}, 500
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ('xls', 'xlsx'):
            # handle optional sheet parameter: empty string -> first sheet
            sheet_param = request.form.get('sheet')
            if sheet_param is None or str(sheet_param).strip() == '':
                sheet = 0
            else:
                # try integer index, otherwise treat as sheet name
                try:
                    sheet = int(sheet_param)
                except ValueError:
                    sheet = sheet_param
            try:
                df = pd.read_excel(dest, sheet_name=sheet)
            except ValueError as e:
                # give a helpful message including available sheet names when possible
                try:
                    xl = pd.ExcelFile(dest)
                    sheets = xl.sheet_names
                    return {'error': f'failed reading excel: {e}. Available sheets: {sheets}'}, 400
                except Exception:
                    return {'error': f'failed reading excel: {e}'}, 400
            except Exception as e:
                return {'error': f'failed reading excel: {e}'}, 500
        else:
            try:
                df = pd.read_csv(dest)
            except Exception as e:
                return {'error': f'failed reading csv: {e}'}, 500

        # Optional: allow parameterized column mapping here (skipped: use raw)
        try:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            df.to_csv(DATA_FILE, index=False)
        except Exception as e:
            return {'error': f'failed saving data: {e}'}, 500

        return redirect(url_for('dashboard'))
    return {'error': 'invalid file type'}, 400


@app.route('/data')
def get_data():
    if not os.path.exists(DATA_FILE):
        return jsonify([])
    try:
        import pandas as pd
        df = pd.read_csv(DATA_FILE)
        return df.to_dict(orient='records')
    except Exception as e:
        return {'error': f'failed reading data: {e}'}, 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
