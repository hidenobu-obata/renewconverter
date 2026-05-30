import os
import time
from flask import Flask, render_template, request, send_file, jsonify
from pydub import AudioSegment

app = Flask(__name__)

# --- FFmpegの場所を指定 ---
FFMPEG_DIR = r"C:\Users\obata\Documents\pyhon514\ffmpeg-8.1.1-essentials_build\ffmpeg-8.1.1-essentials_build\bin"
AudioSegment.converter = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
AudioSegment.ffprobe = os.path.join(FFMPEG_DIR, "ffprobe.exe")

# 保存フォルダ設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 仕様: 最大ファイルサイズ 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

def cleanup_old_files():
    """1日（86400秒）以上経過した古いファイルを自動削除する"""
    now = time.time()
    one_day_seconds = 24 * 60 * 60
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            file_modified_time = os.path.getmtime(file_path)
            if (now - file_modified_time) > one_day_seconds:
                try:
                    os.remove(file_path)
                    print(f"自動削除完了(1日経過): {filename}")
                except Exception as e:
                    print(f"削除失敗: {e}")

# ==========================================
# ★ UptimeRobot 専用の軽量死活監視ルート
# ==========================================
@app.route('/health', methods=['GET'])
def health_check():
    # HTMLを返さず「OK」という文字だけを返すため、超軽量でサーバーが落ちません
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    # 人間がアクセスしたついでに、1日経過した古いファイルを掃除
    cleanup_old_files()
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_file():
    # 1. Nullチェック
    if 'file' not in request.files:
        return jsonify({"error": "m4aファイルを選択してください"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "m4aファイルを選択してください"}), 400

    # 2. 拡張子チェック
    if not file.filename.lower().endswith('.m4a'):
        return jsonify({"error": "形式が違うファイルです。m4aファイルを選択ください"}), 400

    # 3. サイズチェック（10MB制限）
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": "10M以内のm4aファイルしか対応できません"}), 400

    input_filename = file.filename
    unique_id = str(int(time.time()))
    output_filename = f"{unique_id}_{input_filename.rsplit('.', 1)[0]}.mp3"
    
    input_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{input_filename}")
    output_path = os.path.join(UPLOAD_FOLDER, output_filename)

    try:
        file.save(input_path)

        # 4. 破損ファイルチェック
        try:
            audio = AudioSegment.from_file(input_path)
        except Exception:
            if os.path.exists(input_path): os.remove(input_path)
            return jsonify({"error": "このファイルは破損したファイルです"}), 400

        # MP3変換
        audio.export(output_path, format="mp3")
        
        # 変換元m4aは即座に削除してサーバーを軽く保つ
        if os.path.exists(input_path): 
            os.remove(input_path)

        return jsonify({"success": True, "download_id": output_filename})

    except Exception as e:
        print(f"システムエラー: {str(e)}")
        # 5. 何らかのシステムエラー
        return jsonify({"error": "システムエラー"}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "ファイルが見つかりません", 404

if __name__ == '__main__':
    print("Server starting at http://127.0.0.1:5001")
    app.run(debug=True, port=5001)