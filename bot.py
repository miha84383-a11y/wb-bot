from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

# --- Создание XLSX (с оформлением) ---
def create_xlsx_file(product_name: str, package_text: str, user_id: int) -> str:
    parts = parse_package(package_text)
    wb = Workbook()
    ws = wb.active
    ws.title = "Карточка товара"

    # --- 1. Заголовки ---
    headers = ["Товар", "Заголовок", "Описание", "Ключевые слова", "Хэштеги"]
    ws.append(headers)

    # --- 2. Стили ---
    # Шрифт для заголовков (жирный, белый)
    header_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
    # Шрифт для данных (обычный, черный)
    data_font = Font(name='Arial', size=11, color='000000')
    # Фон для заголовков (темно-синий)
    header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    # Фон для данных (светло-серый, для чередования)
    data_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    # Границы
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Применяем стили к заголовкам
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    # --- 3. Ширина колонок ---
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 70
    ws.column_dimensions["D"].width = 35
    ws.column_dimensions["E"].width = 35

    # --- 4. Данные ---
    row_data = [product_name, parts["heading"], parts["description"], parts["keywords"], parts["hashtags"]]
    ws.append(row_data)

    # Применяем стили к строке с данными
    for cell in ws[2]:
        cell.font = data_font
        cell.fill = data_fill
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.border = thin_border

    # Авто-высота строки
    ws.row_dimensions[2].height = None

    # --- 5. Сохранение ---
    xlsx_path = f"temp_{user_id}.xlsx"
    wb.save(xlsx_path)
    return xlsx_path
