from flask import Flask, render_template, request, jsonify, g
import re
import sqlite3
import os
import sys
import json
import subprocess
import traceback
import unicodedata
from pathlib import Path
from werkzeug.utils import secure_filename


def get_writable_dir() -> str:
    """Directory for writable files (like the SQLite DB)."""
    if os.getenv('VERCEL'):
        # Vercel filesystem is read-only except /tmp
        d = '/tmp/silgon'
        os.makedirs(d, exist_ok=True)
        return d
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def get_resource_dir() -> str:
    """Directory for bundled resources (templates/static).

    In PyInstaller, data files usually live under sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(__file__)


WRITABLE_DIR = get_writable_dir()
RESOURCE_DIR = get_resource_dir()

# Back-compat: other modules import BASE_DIR
BASE_DIR = WRITABLE_DIR

DB_PATH = os.path.join(WRITABLE_DIR, 'silgon.db')
ATTACHMENTS_ROOT = Path(WRITABLE_DIR)
ATTACHMENTS_META_FILE = '.anexos_meta.json'


def _normalize_folder_part(value: str, fallback: str = 'SEM_INFO') -> str:
    s = str(value or '').strip()
    if not s:
        return fallback
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^A-Za-z0-9_\-]', '', s)
    s = s.strip('_-')
    return s or fallback


def build_prontuario_folder_name(cpf: str, patient_name: str, prontuario_label: str) -> str:
    cpf_digits = re.sub(r'\D', '', str(cpf or ''))
    cpf_part = _normalize_folder_part(cpf_digits, 'SEM_CPF')
    name_part = _normalize_folder_part(patient_name, 'SEM_NOME')
    prontuario_part = _normalize_folder_part(prontuario_label, 'SEM_PRONTUARIO')
    return f'{cpf_part}_{name_part}_{prontuario_part}'


def get_attachments_dir(cpf: str, patient_name: str, prontuario_label: str) -> Path:
    folder = build_prontuario_folder_name(cpf, patient_name, prontuario_label)
    return ATTACHMENTS_ROOT / folder / 'anexos'


def ensure_safe_path(path: Path) -> Path:
    resolved = path.resolve()
    root = ATTACHMENTS_ROOT.resolve()
    if os.path.commonpath([str(resolved), str(root)]) != str(root):
        raise ValueError('Caminho inválido')
    return resolved


def get_attachments_meta_path(target_dir: Path) -> Path:
    return target_dir / ATTACHMENTS_META_FILE


def load_attachments_meta(target_dir: Path) -> dict:
    meta_path = get_attachments_meta_path(target_dir)
    if not meta_path.exists() or not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_attachments_meta(target_dir: Path, meta: dict) -> None:
    meta_path = get_attachments_meta_path(target_dir)
    meta_path.write_text(json.dumps(meta or {}, ensure_ascii=False, indent=2), encoding='utf-8')


def open_in_os(path: Path) -> None:
    if sys.platform.startswith('win'):
        os.startfile(str(path))
        return
    if sys.platform == 'darwin':
        subprocess.Popen(['open', str(path)])
        return
    subprocess.Popen(['xdg-open', str(path)])


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT,
                date TEXT,
                time TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT UNIQUE,
                name TEXT,
                tel_home TEXT,
                tel_cell TEXT,
                tel_msg TEXT,
                email TEXT,
                cep TEXT,
                address TEXT,
                number TEXT,
                complement TEXT,
                prof TEXT,
                age INTEGER,
                weight REAL,
                height REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()


def ensure_patients_schema():
    """Ensure patients table has expected columns; add missing ones via ALTER TABLE."""
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    try:
        cur.execute("PRAGMA table_info(patients)")
        cols = [r[1] for r in cur.fetchall()]
        # if the table is completely missing, create it with the expected schema
        if not cols:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cpf TEXT UNIQUE,
                    name TEXT,
                    tel_home TEXT,
                    tel_cell TEXT,
                    tel_msg TEXT,
                    email TEXT,
                    cep TEXT,
                    address TEXT,
                    number TEXT,
                    complement TEXT,
                    prof TEXT,
                    age INTEGER,
                    weight REAL,
                    height REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.commit()
            return
        expected = {
            'cpf': 'TEXT', 'name': 'TEXT', 'tel_home': 'TEXT', 'tel_cell': 'TEXT', 'tel_msg': 'TEXT',
            'email': 'TEXT', 'cep': 'TEXT', 'address': 'TEXT', 'number': 'TEXT', 'complement': 'TEXT',
            'prof': 'TEXT', 'age': 'INTEGER', 'weight': 'REAL', 'height': 'REAL'
        }
        for col, coltype in expected.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE patients ADD COLUMN {col} {coltype}")
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def ensure_appointments_schema():
    """Ensure appointments table exists; create if missing."""
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    try:
        cur.execute("PRAGMA table_info(appointments)")
        cols = [r[1] for r in cur.fetchall()]
        if not cols:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    date TEXT,
                    time TEXT,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


TEMPLATES_DIR = os.path.join(RESOURCE_DIR, 'templates')
STATIC_DIR = os.path.join(RESOURCE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
_BOOT_ERROR = None


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.route('/api/<path:_path>', methods=['OPTIONS'])
def api_options(_path):
    return ('', 204)


@app.errorhandler(Exception)
def handle_api_exception(e):
    # For API routes, return JSON with message to ease diagnosis in Vercel logs/UI.
    if request.path.startswith('/api/'):
        try:
            tb = traceback.format_exc(limit=3)
        except Exception:
            tb = ''
        return jsonify({'status': 'error', 'message': str(e), 'trace': tb}), 500
    raise e


@app.route('/favicon.ico')
def favicon():
    # return a tiny inline SVG as favicon to avoid 404 in browser logs
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'>"
           "<rect width='64' height='64' rx='12' fill='#2e8b57'/><text x='50%' y='54%' font-size='36' "
           "text-anchor='middle' fill='white' font-family='Arial' font-weight='700'>S</text></svg>")
    from flask import Response
    return Response(svg, mimetype='image/svg+xml')


@app.route('/robots.txt')
def robots():
    return '', 204


@app.route('/api/appointments/<int:appt_id>', methods=['DELETE'])
def delete_appointment(appt_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM appointments WHERE id=?', (appt_id,))
    db.commit()
    return jsonify({'status': 'ok'})


# Flask 3 removed `before_first_request`; initialize DB explicitly before running
def ensure_initialized():
    init_db()
    # ensure patients table has required columns for current UI
    ensure_patients_schema()
    ensure_appointments_schema()


try:
    # Important for serverless (e.g., Vercel): __main__ is not executed.
    ensure_initialized()
except Exception as _e:
    _BOOT_ERROR = str(_e)


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/appointments', methods=['GET', 'POST'])
def appointments():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    db = get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        # debug: log incoming payload to help diagnose client-side save errors
        try:
            print('DEBUG /api/patients POST payload:', data)
        except Exception:
            pass
        patient_name = data.get('patient_name', '')
        date = data.get('date', '')
        time = data.get('time', '')
        reason = data.get('reason', '')
        cur = db.cursor()
        cur.execute('INSERT INTO appointments (patient_name, date, time, reason) VALUES (?,?,?,?)',
                    (patient_name, date, time, reason))
        db.commit()
        return jsonify({'status': 'ok', 'id': cur.lastrowid})
    else:
        cur = db.execute('SELECT * FROM appointments ORDER BY created_at DESC LIMIT 100')
        rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)


@app.route('/api/patients', methods=['GET', 'POST'])
def patients():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    db = get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        # if id provided, update; otherwise insert
        pid = data.get('id')
        fields = ['cpf','name','tel_home','tel_cell','tel_msg','email','cep','address','number','complement','prof','age','weight','height']
        values = [data.get(f) for f in fields]
        cur = db.cursor()
        if pid:
            # update only columns that exist in current schema
            sets = ','.join([f"{f}=?" for f in fields])
            cur.execute(f'UPDATE patients SET {sets} WHERE id=?', values + [pid])
            db.commit()
            return jsonify({'status':'ok','id': pid})
        else:
            # check duplicate CPF before inserting
            cpf_val = data.get('cpf')
            if cpf_val:
                cur.execute('SELECT * FROM patients WHERE cpf=?', (cpf_val,))
                existing = cur.fetchone()
                if existing:
                    # return 409 Conflict with existing patient data so frontend can prompt
                    return (jsonify({'status': 'exists', 'id': existing['id'], 'patient': dict(existing)}), 409)
            placeholders = ','.join(['?']*len(fields))
            cols = ','.join(fields)
            try:
                cur.execute(f'INSERT INTO patients ({cols}) VALUES ({placeholders})', values)
                db.commit()
                return jsonify({'status':'ok','id': cur.lastrowid})
            except sqlite3.IntegrityError:
                # unique constraint violation (cpf) — fetch conflicting row and return 409
                if cpf_val:
                    cur.execute('SELECT * FROM patients WHERE cpf=?', (cpf_val,))
                    existing = cur.fetchone()
                    if existing:
                        return (jsonify({'status': 'exists', 'id': existing['id'], 'patient': dict(existing)}), 409)
                return (jsonify({'status': 'error', 'message': 'Integrity error'}), 400)
    else:
        # support optional CPF query to fetch a single patient without returning whole DB
        cpf_q = request.args.get('cpf')
        if cpf_q:
            # normalize to digits
            cpf_digits = re.sub(r'\D', '', cpf_q)  # Normalize to digits
            # perform a safe query matching digits-only cpf (remove dots, dashes, spaces)
            cur = db.execute("SELECT * FROM patients WHERE REPLACE(REPLACE(REPLACE(cpf,'.',''),'-',''),' ','') = ?", (cpf_digits,))
            rows = [dict(r) for r in cur.fetchall()]
            return jsonify(rows)
        cur = db.execute('SELECT * FROM patients ORDER BY name COLLATE NOCASE')
        rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)


@app.route('/api/patients/<int:pid>', methods=['DELETE'])
def delete_patient(pid):
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM patients WHERE id=?', (pid,))
    db.commit()
    return jsonify({'status':'ok'})


@app.route('/api/attachments', methods=['GET'])
def list_attachments():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    cpf = request.args.get('cpf', '')
    patient_name = request.args.get('patient_name', '')
    prontuario_label = request.args.get('prontuario_label', '')

    if not cpf or not patient_name or not prontuario_label:
        return jsonify({'status': 'error', 'message': 'Parâmetros obrigatórios ausentes.'}), 400

    try:
        target_dir = ensure_safe_path(get_attachments_dir(cpf, patient_name, prontuario_label))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Diretório inválido.'}), 400

    if not target_dir.exists():
        return jsonify({'status': 'ok', 'items': [], 'folder': str(target_dir)})

    meta = load_attachments_meta(target_dir)
    items = []
    for p in sorted(target_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file():
            continue
        if p.name == ATTACHMENTS_META_FILE:
            continue
        st = p.stat()
        items.append({
            'name': p.name,
            'size': st.st_size,
            'modified_at': st.st_mtime,
            'attachment_type': str(meta.get(p.name, '') or ''),
            'folder': str(target_dir)
        })

    return jsonify({'status': 'ok', 'items': items, 'folder': str(target_dir)})


@app.route('/api/attachments/upload', methods=['POST'])
def upload_attachments():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    cpf = request.form.get('cpf', '')
    patient_name = request.form.get('patient_name', '')
    prontuario_label = request.form.get('prontuario_label', '')

    if not cpf or not patient_name or not prontuario_label:
        return jsonify({'status': 'error', 'message': 'CPF, nome e prontuário são obrigatórios.'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'status': 'error', 'message': 'Nenhum arquivo recebido.'}), 400

    try:
        target_dir = ensure_safe_path(get_attachments_dir(cpf, patient_name, prontuario_label))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Diretório inválido.'}), 400

    target_dir.mkdir(parents=True, exist_ok=True)

    types_json = request.form.get('file_types_json', '[]')
    file_types = []
    try:
        parsed = json.loads(types_json)
        if isinstance(parsed, list):
            file_types = [str(x or '') for x in parsed]
    except Exception:
        file_types = []

    meta = load_attachments_meta(target_dir)

    saved = []
    for idx_file, f in enumerate(files):
        original = secure_filename(f.filename or '')
        if not original:
            continue
        base = Path(original).stem
        ext = Path(original).suffix
        dest = target_dir / original
        idx = 1
        while dest.exists():
            dest = target_dir / f'{base}_{idx}{ext}'
            idx += 1
        f.save(str(dest))
        saved.append(dest.name)
        file_type = file_types[idx_file] if idx_file < len(file_types) else ''
        if file_type:
            meta[dest.name] = file_type

    save_attachments_meta(target_dir, meta)

    return jsonify({'status': 'ok', 'saved': saved, 'folder': str(target_dir)})


@app.route('/api/attachments/open', methods=['POST'])
def open_attachment():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    data = request.get_json() or {}
    cpf = data.get('cpf', '')
    patient_name = data.get('patient_name', '')
    prontuario_label = data.get('prontuario_label', '')
    filename = data.get('filename', '')
    open_folder = bool(data.get('open_folder'))

    if not cpf or not patient_name or not prontuario_label:
        return jsonify({'status': 'error', 'message': 'CPF, nome e prontuário são obrigatórios.'}), 400

    try:
        target_dir = ensure_safe_path(get_attachments_dir(cpf, patient_name, prontuario_label))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Diretório inválido.'}), 400

    if open_folder:
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            open_in_os(target_dir)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Falha ao abrir pasta: {e}'}), 500

    if not filename:
        return jsonify({'status': 'error', 'message': 'Arquivo não informado.'}), 400

    safe_name = Path(secure_filename(str(filename))).name
    file_path = target_dir / safe_name
    try:
        file_path = ensure_safe_path(file_path)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Arquivo inválido.'}), 400

    if not file_path.exists() or not file_path.is_file():
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado.'}), 404

    try:
        open_in_os(file_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Falha ao abrir arquivo: {e}'}), 500


@app.route('/api/attachments/delete', methods=['POST'])
def delete_attachment():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    data = request.get_json() or {}
    cpf = data.get('cpf', '')
    patient_name = data.get('patient_name', '')
    prontuario_label = data.get('prontuario_label', '')
    filename = data.get('filename', '')

    if not cpf or not patient_name or not prontuario_label:
        return jsonify({'status': 'error', 'message': 'CPF, nome e prontuário são obrigatórios.'}), 400
    if not filename:
        return jsonify({'status': 'error', 'message': 'Arquivo não informado.'}), 400

    try:
        target_dir = ensure_safe_path(get_attachments_dir(cpf, patient_name, prontuario_label))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Diretório inválido.'}), 400

    safe_name = Path(secure_filename(str(filename))).name
    file_path = target_dir / safe_name
    try:
        file_path = ensure_safe_path(file_path)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Arquivo inválido.'}), 400

    if not file_path.exists() or not file_path.is_file():
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado.'}), 404

    try:
        file_path.unlink()
        meta = load_attachments_meta(target_dir)
        if safe_name in meta:
            meta.pop(safe_name, None)
            save_attachments_meta(target_dir, meta)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Falha ao excluir arquivo: {e}'}), 500


@app.route('/api/attachments/type', methods=['POST'])
def update_attachment_type():
    if _BOOT_ERROR:
        return jsonify({'status': 'error', 'message': f'Falha na inicialização: {_BOOT_ERROR}', 'db_path': DB_PATH}), 500
    data = request.get_json() or {}
    cpf = data.get('cpf', '')
    patient_name = data.get('patient_name', '')
    prontuario_label = data.get('prontuario_label', '')
    filename = data.get('filename', '')
    attachment_type = str(data.get('attachment_type', '') or '').strip()

    if not cpf or not patient_name or not prontuario_label:
        return jsonify({'status': 'error', 'message': 'CPF, nome e prontuário são obrigatórios.'}), 400
    if not filename:
        return jsonify({'status': 'error', 'message': 'Arquivo não informado.'}), 400

    try:
        target_dir = ensure_safe_path(get_attachments_dir(cpf, patient_name, prontuario_label))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Diretório inválido.'}), 400

    safe_name = Path(secure_filename(str(filename))).name
    file_path = target_dir / safe_name
    try:
        file_path = ensure_safe_path(file_path)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Arquivo inválido.'}), 400

    if not file_path.exists() or not file_path.is_file():
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado.'}), 404

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        meta = load_attachments_meta(target_dir)
        if attachment_type:
            meta[safe_name] = attachment_type
        else:
            meta.pop(safe_name, None)
        save_attachments_meta(target_dir, meta)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Falha ao salvar tipo: {e}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    writable = os.access(WRITABLE_DIR, os.W_OK)
    db_exists = os.path.exists(DB_PATH)
    return jsonify({
        'status': 'ok' if not _BOOT_ERROR else 'error',
        'boot_error': _BOOT_ERROR,
        'vercel': bool(os.getenv('VERCEL')),
        'writable_dir': WRITABLE_DIR,
        'writable': writable,
        'db_path': DB_PATH,
        'db_exists': db_exists,
    })


if __name__ == '__main__':
    ensure_initialized()
    host = os.getenv('SILGON_HOST', '0.0.0.0')
    port = int(os.getenv('SILGON_PORT', '5000'))
    debug = os.getenv('SILGON_DEBUG', '1') == '1'
    app.run(host=host, port=port, debug=debug)
