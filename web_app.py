# web_app.py
import os
import asyncio
import csv
import tempfile
from pathlib import Path
from flask import Flask, request, render_template_string, send_file, jsonify
from werkzeug.utils import secure_filename

from app import generate_full_package

app = Flask(__name__)

# Папка для временных файлов
TEMP_DIR = Path(__file__).parent / "temp_files"
TEMP_DIR.mkdir(exist_ok=True)

# --- HTML шаблон (с двумя формами и AJAX) ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Генератор описаний WB/Ozon</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #fff; margin: 0; padding: 2rem; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .card { background: #fafafa; border: 1px solid #ddd; border-radius: 8px; padding: 2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.1); max-width: 800px; width: 100%; }
        h1 { margin-top: 0; }
        .form-group { margin-bottom: 1rem; }
        .btn { display: inline-block; margin-top: 0.5rem; padding: 0.6rem 1.2rem; background: #3b82f6; color: #fff; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
        .btn:hover { background: #2563eb; }
        .error { color: #b00; margin-bottom: 1rem; }
        .description { margin-top: 1rem; padding: 1rem; background: #e5e7eb; border: 1px solid #9ca3af; border-radius: 4px; white-space: pre-wrap; }
        .download-btn { display: inline-block; margin-top: 1rem; margin-right: 1rem; padding: 0.6rem 1.2rem; background: #10b981; color: #fff; text-decoration: none; border-radius: 4px; }
        .progress { color: #666; font-style: italic; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Генератор описаний товаров</h1>

        <div class="form-group">
            <label for="product">Название товара (для одного товара):</label><br>
            <input type="text" id="product" name="product" placeholder="Введите название товара">
            <button type="button" class="btn" onclick="generateSingle()">Сгенерировать описание</button>
        </div>

        <div class="form-group">
            <label for="file">Загрузить файл (.xlsx или .csv) для обработки нескольких товаров:</label><br>
            <input type="file" id="file" name="file" accept=".xlsx,.csv">
            <button type="button" class="btn" onclick="generateFile()">Обработать файл</button>
        </div>

        <div id="progress" class="progress" style="display:none;">Обработка...</div>
        <div id="error" class="error" style="display:none;"></div>
        <div id="result" class="description" style="display:none;"></div>
        <div id="downloads"></div>
    </div>

    <script>
        async function generateSingle() {
            const product = document.getElementById('product').value.trim();
            if (!product) {
                alert('Введите название товара');
                return;
            }
            document.getElementById('progress').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('result').style.display = 'none';
            document.getElementById('downloads').innerHTML = '';

            try {
                const resp = await fetch('/generate_single', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({product_name: product})
                });
                const data = await resp.json();
                document.getElementById('progress').style.display = 'none';
                if (data.error) {
                    document.getElementById('error').textContent = '❌ ' + data.error;
                    document.getElementById('error').style.display = 'block';
                } else {
                    document.getElementById('result').textContent = data.description;
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('downloads').innerHTML =
                        `<a href="/download_file?file=${encodeURIComponent(data.pdf_file)}" class="download-btn">📄 Скачать PDF</a>` +
                        `<a href="/download_file?file=${encodeURIComponent(data.xlsx_file)}" class="download-btn">📊 Скачать Excel</a>`;
                }
            } catch (e) {
                document.getElementById('progress').style.display = 'none';
                document.getElementById('error').textContent = '❌ Ошибка сети: ' + e.message;
                document.getElementById('error').style.display = 'block';
            }
        }

        async function generateFile() {
            const fileInput = document.getElementById('file');
            if (!fileInput.files.length) {
                alert('Выберите файл');
                return;
            }
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            document.getElementById('progress').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('result').style.display = 'none';
            document.getElementById('downloads').innerHTML = '';

            try {
                const resp = await fetch('/generate_file', { method: 'POST', body: formData });
                const data = await resp.json();
                document.getElementById('progress').style.display = 'none';
                if (data.error) {
                    document.getElementById('error').textContent = '❌ ' + data.error;
                    document.getElementById('error').style.display = 'block';
                } else {
                    document.getElementById('result').textContent = data.message;
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('downloads').innerHTML =
                        `<a href="/download_file?file=${encodeURIComponent(data.xlsx_file)}" class="download-btn">📊 Скачать Excel</a>` +
                        `<a href="/download_file?file=${encodeURIComponent(data.pdf_file)}" class="download-btn">📄 Скачать PDF</a>`;
                }
            } catch (e) {
                document.getElementById('progress').style.display = 'none';
                document.getElementById('error').textContent = '❌ Ошибка сети: ' + e.message;
                document.getElementById('error').style.display = 'block';
            }
        }
    </script>
</body>
</html>
"""

# --- Вспомогательные функции ---

def create_xlsx_file(results: list, user_id: int = 0) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    wb = Workbook()
    ws = wb.active
    ws.title = "Карточки товаров"
    headers = ["Товар", "Заголовок", "Описание", "Ключевые слова", "Хэштеги"]
    ws.append(headers)
    header_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
    data_font = Font(name='Arial', size=11, color='000000')
    header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    data_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 20
    for i, result in enumerate(results, 2):
        ws.cell(row=i, column=1, value=result.get("product", ""))
        ws.cell(row=i, column=2, value=result.get("heading", ""))
        ws.cell(row=i, column=3, value=result.get("description", ""))
        ws.cell(row=i, column=4, value=result.get("keywords", ""))
        ws.cell(row=i, column=5, value=result.get("hashtags", ""))
        for cell in ws[i]:
            cell.font = data_font
            cell.fill = data_fill
            cell.border = thin_border
            cell.alignment = Alignment(vertical='top', wrap_text=True)
    xlsx_path = str(TEMP_DIR / f"products_{user_id}.xlsx")
    wb.save(xlsx_path)
    return xlsx_path

def create_pdf_file(results: list, user_id: int = 0) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT
    pdf_path = str(TEMP_DIR / f"products_{user_id}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        font_name = 'DejaVuSans'
    except:
        font_name = 'Helvetica'
    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle('Normal', fontName=font_name, fontSize=10, leading=14, alignment=TA_LEFT)
    style_bold = ParagraphStyle('Bold', fontName=font_name, fontSize=12, leading=16, spaceAfter=6)
    style_title = ParagraphStyle('Title', fontName=font_name, fontSize=16, leading=20, spaceAfter=12, alignment=1)
    elements = []
    for idx, res in enumerate(results):
        if idx > 0:
            elements.append(PageBreak())
        elements.append(Paragraph(f"<b>Товар:</b> {res.get('product', '')}", style_title))
        elements.append(Paragraph(f"<b>Заголовок:</b> {res.get('heading', '')}", style_bold))
        elements.append(Paragraph(f"<b>Описание:</b> {res.get('description', '')}", style_normal))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(f"<b>Ключевые слова:</b> {res.get('keywords', '')}", style_normal))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(f"<b>Хэштеги:</b> {res.get('hashtags', '')}", style_normal))
        elements.append(Spacer(1, 50*mm))
    doc.build(elements)
    return pdf_path

# --- Маршруты ---

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/generate_single", methods=["POST"])
def generate_single():
    data = request.get_json()
    product_name = data.get("product_name", "").strip()
    if not product_name:
        return jsonify({"error": "Не указано название товара"}), 400
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_full_package(product_name))
        loop.close()
        if not isinstance(result, dict) or result.get("error"):
            return jsonify({"error": "Не удалось сгенерировать описание"}), 500
        item = {
            "product": product_name,
            "heading": result.get("header", "")[:50],
            "description": result.get("description", ""),
            "keywords": result.get("keywords", ""),
            "hashtags": result.get("hashtags", "")
        }
        xlsx_path = create_xlsx_file([item], 0)
        pdf_path = create_pdf_file([item], 0)
        description = (
            f"--- Заголовок ({len(item['heading'])} символов) ---\n{item['heading']}\n\n"
            f"--- Описание (продающее) ---\n{item['description']}\n\n"
            f"--- Ключевые слова ---\n{item['keywords']}\n\n"
            f"--- Хэштеги ---\n{item['hashtags']}"
        )
        return jsonify({
            "description": description,
            "xlsx_file": os.path.basename(xlsx_path),
            "pdf_file": os.path.basename(pdf_path)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_file", methods=["POST"])
def generate_file():
    if "file" not in request.files:
        return jsonify({"error": "Файл не загружен"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Пустое имя файла"}), 400
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["xlsx", "csv"]:
        return jsonify({"error": "Неподдерживаемый формат. Используйте .xlsx или .csv"}), 400

    file_path = str(TEMP_DIR / f"upload_{secure_filename(file.filename)}")
    file.save(file_path)

    products = []
    try:
        if ext == "xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(file_path, read_only=True)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] is not None:
                    products.append(str(row[0]).strip())
            wb.close()
        elif ext == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if row and row[0] is not None:
                        products.append(str(row[0]).strip())
    except Exception as e:
        os.remove(file_path)
        return jsonify({"error": f"Ошибка чтения файла: {e}"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    if not products:
        return jsonify({"error": "В файле не найдено товаров"}), 400

    all_results = []
    for p in products:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(generate_full_package(p))
            loop.close()
            if isinstance(result, dict) and not result.get("error"):
                all_results.append({
                    "product": p,
                    "heading": result.get("header", "")[:50],
                    "description": result.get("description", ""),
                    "keywords": result.get("keywords", ""),
                    "hashtags": result.get("hashtags", "")
                })
            else:
                all_results.append({"product": p, "heading": "Ошибка генерации", "description": "", "keywords": "", "hashtags": ""})
        except Exception as e:
            all_results.append({"product": p, "heading": "Ошибка генерации", "description": "", "keywords": "", "hashtags": ""})

    xlsx_path = create_xlsx_file(all_results, 0)
    pdf_path = create_pdf_file(all_results, 0)
    failed = sum(1 for r in all_results if r["heading"] == "Ошибка генерации")
    message = f"Обработано {len(all_results)} товаров."
    if failed:
        message += f" Ошибок: {failed}."
    return jsonify({
        "message": message,
        "xlsx_file": os.path.basename(xlsx_path),
        "pdf_file": os.path.basename(pdf_path)
    })

@app.route("/download_file")
def download_file():
    fname = request.args.get("file")
    if not fname:
        return "Не указано имя файла", 400
    path = TEMP_DIR / fname
    if not path.exists():
        return "Файл не найден", 404
    return send_file(str(path), as_attachment=True, download_name=fname)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
