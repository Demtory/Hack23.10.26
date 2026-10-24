"""Сборка питч-деки «ОТТОК · Risk Desk» (python-pptx).

Строгое соответствие Brand Guidelines Aéza:
- Цвета:
    * PANTONE 298 C (#4CC6F1) — основной светло-голубой акцент
    * PANTONE BLACK C (#000000) — глубокий базовый чёрный
    * PANTONE COOL GRAY 1 C (#F4F4F4) — нейтральный светлый фон
    * PANTONE 534 C (#182D48) — тёмно-синий индиго для контрастных карточек
    * PANTONE 7579 C (#E97C35) — фирменный оранжевый акцент для риска
- Шрифты:
    * Exo 2 — основной (заголовки, цифры, акценты)
    * Inter — дополнительный (подписи, списки, буллеты)
- Структура (7 слайдов на 3 минуты):
    1. Титул (18 сек) — позиционирование
    2. Специфика хостинга (32 сек) — 67,53 € под риском, suspended/prolong_wait
    3. Решение кейса (25 сек) — большой чёткий скриншот дашборда
    4. Действие и retention (25 сек) — крупное окно персонального письма
    5. Методология и честность (30 сек) — почему не ML, 7 признаков, формула денег
    6. Инженерия и прод (25 сек) — docker compose up, 449 тестов, 10 000 клиентов
    7. Итог и Q&A (15 сек) — результат, прямой QR-код, Swagger, /metrics

Запуск:
    python pitch/build_pitch.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
try:
    import qrcode
except ImportError:  # QR-файлы уже лежат в pitch/, генерация не нужна
    qrcode = None

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
PITCH_DIR = Path(__file__).resolve().parent
# Актуальная дека собирается вручную; скрипт оставлен как исторический.
OUT = PITCH_DIR / "generated-deck.pptx"
TOTAL_SLIDES = 8
QR_PATH = PITCH_DIR / "qr-repo.png"
DEMO_QR_PATH = PITCH_DIR / "qr-demo.png"
LOGO_PATH = PITCH_DIR / "aeza-logo.png"
MARK_PATH = PITCH_DIR / "aeza-mark.png"
DASH_CROP_PATH = PITCH_DIR / "dashboard-crop.png"
EMAIL_CROP_PATH = PITCH_DIR / "email-crop.png"

REPO_URL = "https://github.com/Demtory/Hack23.10.26"

# Фирменная палитра Aéza Brand Guidelines
PANTONE_298C = RGBColor(0x4C, 0xC6, 0xF1)     # Основной светло-голубой
PANTONE_BLACK = RGBColor(0x00, 0x00, 0x00)    # Базовый чёрный
PANTONE_GRAY = RGBColor(0xF4, 0xF4, 0xF4)     # Cool Gray 1 C (нейтральный фон)
PANTONE_NAVY = RGBColor(0x18, 0x2D, 0x48)     # Pantone 534 C (тёмно-синий)
PANTONE_ORANGE = RGBColor(0xE9, 0x7C, 0x35)   # Pantone 7579 C (акцентный оранжевый для риска)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE_COLOR = RGBColor(0xDD, 0xE2, 0xEA)

HEAD = "Exo 2"
BODY = "Inter"

W, H = 13.333, 7.5
MARGIN = 0.85


def ensure_assets() -> None:
    # 1. Прямой QR-код без редиректов
    if not QR_PATH.exists() and qrcode is not None:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=2,
        )
        qr.add_data(REPO_URL)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(QR_PATH))

    # 2. Крупный скриншот дашборда (верхний вьюпорт 1440x920)
    if not DASH_CROP_PATH.exists() and (SHOTS / "02-overview-1440.png").exists():
        im1 = Image.open(str(SHOTS / "02-overview-1440.png"))
        crop1 = im1.crop((0, 0, 1440, 920))
        crop1.save(str(DASH_CROP_PATH))

    # 3. Крупный скриншот модального окна письма (центрированный бокс)
    if not EMAIL_CROP_PATH.exists() and (SHOTS / "10-email-dialog.png").exists():
        im2 = Image.open(str(SHOTS / "10-email-dialog.png"))
        crop2 = im2.crop((440, 75, 1000, 825))
        crop2.save(str(EMAIL_CROP_PATH))


def rgb_text(box, value, size, *, bold=False, color=PANTONE_BLACK, font=BODY, align=PP_ALIGN.LEFT,
             line_spacing=1.15, space_after=0):
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = value.split("\n")
    for index, line in enumerate(lines):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.alignment = align
        paragraph.line_spacing = line_spacing
        paragraph.space_after = Pt(space_after)
        run = paragraph.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def text(slide, left, top, width, height, value, size, **kwargs):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    return rgb_text(box, value, size, **kwargs)


def bullets(slide, left, top, width, height, items, *, size=17, gap=12, color=PANTONE_BLACK):
    """items: список кортежей (level, bold_prefix, text_body)."""
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for index, item in enumerate(items):
        level = item[0]
        prefix_bold = item[1]
        body = item[2]

        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.line_spacing = 1.25
        paragraph.space_after = Pt(gap)
        _hanging_indent(paragraph, level)

        marker = paragraph.add_run()
        marker.text = "—  " if level == 0 else "   ·  "
        marker.font.size = Pt(size)
        marker.font.color.rgb = PANTONE_298C if level == 0 else PANTONE_NAVY
        marker.font.bold = True
        marker.font.name = HEAD

        if prefix_bold:
            bold_run = paragraph.add_run()
            bold_run.text = prefix_bold + " "
            bold_run.font.size = Pt(size)
            bold_run.font.bold = True
            bold_run.font.color.rgb = color
            bold_run.font.name = HEAD

        run = paragraph.add_run()
        run.text = body
        run.font.size = Pt(size)
        run.font.bold = False
        run.font.color.rgb = color
        run.font.name = BODY
    return box


def _hanging_indent(paragraph, level: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    left = 0.0 if level == 0 else 0.35
    p_pr.set("marL", str(int(Inches(left + 0.35))))
    p_pr.set("indent", str(int(-Inches(0.35))))


def rect(slide, left, top, width, height, color, *, line=None, radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1.5)
    shape.shadow.inherit = False
    sp_pr = shape._element.spPr
    if sp_pr.find(qn("a:effectLst")) is None:
        sp_pr.append(sp_pr.makeelement(qn("a:effectLst"), {}))
    if radius:
        shape.adjustments[0] = 0.06
    return shape


def new_slide(prs, *, background=WHITE, footer=True, number=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = background

    rect(slide, 0, 0, W, 0.08, PANTONE_298C)

    if footer:
        rect(slide, MARGIN, 7.02, W - 2 * MARGIN, 0.015, LINE_COLOR)
        if MARK_PATH.exists():
            image(slide, MARK_PATH, MARGIN, 7.06, 0.22, border=False)
        text(slide, MARGIN + 0.32, 7.08, 6, 0.3, "AÉZA · ОТТОК · Risk Desk", 10, bold=True, color=PANTONE_NAVY, font=HEAD)
        if number is not None:
            text(slide, W - MARGIN - 0.8, 7.08, 0.8, 0.3, f"{number:02d} / {TOTAL_SLIDES:02d}", 10, bold=True, color=PANTONE_NAVY,
                 align=PP_ALIGN.RIGHT, font=HEAD)
    return slide


def eyebrow(slide, value):
    text(slide, MARGIN, 0.45, 9, 0.3, value.upper(), 11, bold=True, color=PANTONE_NAVY, font=HEAD)


def title(slide, value, *, size=34, top=0.82, width=11.6):
    text(slide, MARGIN, top, width, 0.95, value, size, bold=True, font=HEAD, color=PANTONE_BLACK)
    rect(slide, MARGIN, top + 0.98, 1.2, 0.07, PANTONE_298C)


def image(slide, path, left, top, width, *, height=None, border=True):
    kwargs = {"width": Inches(width)}
    if height is not None:
        kwargs["height"] = Inches(height)
    picture = slide.shapes.add_picture(str(path), Inches(left), Inches(top), **kwargs)
    if border:
        picture.line.color.rgb = LINE_COLOR
        picture.line.width = Pt(1.5)
    return picture


def note(slide, value):
    slide.notes_slide.notes_text_frame.text = value


def build(output_path: Path = OUT) -> Path:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    ensure_assets()

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 1 ─ ТИТУЛ (24 слова | ~15-18 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, background=PANTONE_GRAY, footer=False)

    rect(slide, 0, 0, 0.35, H, PANTONE_298C)
    rect(slide, 0.35, 0, 0.08, H, PANTONE_NAVY)

    if LOGO_PATH.exists():
        image(slide, LOGO_PATH, MARGIN + 0.2, 0.8, 2.2, border=False)

    text(slide, MARGIN + 0.2, 1.65, 10, 0.4, "ХАКАТОН РНД · УРОВЕНЬ MIDDLE · КЕЙС AÉZA", 13, bold=True, color=PANTONE_NAVY, font=HEAD)
    text(slide, MARGIN + 0.2, 2.15, 11, 1.4, "ОТТОК · Risk Desk", 56, bold=True, font=HEAD, color=PANTONE_BLACK)
    text(slide, MARGIN + 0.2, 3.6, 10.5, 0.8, "Кому звонить сегодня, почему и что сказать", 26, bold=True, color=PANTONE_NAVY, font=HEAD)
    rect(slide, MARGIN + 0.2, 4.65, 1.8, 0.08, PANTONE_298C)

    text(slide, MARGIN + 0.2, 4.95, 9.2, 0.8,
         "Панель маркетолога облачного хостинга:\n"
         "Анализ биллинга  →  Приоритет клиентов  →  Спасение в 1 клик",
         17, bold=True, color=PANTONE_NAVY, font=BODY)

    text(slide, MARGIN + 0.2, 6.45, 9.0, 0.4,
         "FastAPI · React 18 · SQLite WAL · Docker Compose · 449 тестов",
         13, bold=True, color=PANTONE_BLACK, font=HEAD)

    # Мини-QR на титуле
    rect(slide, W - MARGIN - 1.9, 4.45, 1.9, 2.4, WHITE, line=PANTONE_NAVY, radius=True)
    image(slide, QR_PATH, W - MARGIN - 1.75, 4.6, 1.6, border=False)
    text(slide, W - MARGIN - 1.85, 6.35, 1.8, 0.35, "GitHub проекта", 11, bold=True, align=PP_ALIGN.CENTER, color=PANTONE_NAVY, font=HEAD)

    note(slide,
         "[0:00–0:18 | 24 слова]\n\n"
         "«Здравствуйте! Наша команда представляет Risk Desk — рабочее место маркетолога хостинга. "
         "Мы отвечаем на три вопроса кейса: кому звонить сегодня, почему клиент уходит и сколько бизнес потеряет».")

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 2 ─ СПЕЦИФИКА ХОСТИНГА (42 слова | ~30-35 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, number=2)
    eyebrow(slide, "Специфика хостинга")
    title(slide, "Удалённый сервер вернуть нельзя")

    bullets(slide, MARGIN, 2.35, 6.4, 4.2, [
        (0, "Сервер удалён = клиент потерян.", "Спасать нужно ДО безвозвратного удаления данных."),
        (0, "Точки перехвата оттока:", "suspended (выключил, но платит) и prolong_wait (5 дней до удаления)."),
        (0, "Проблема маркетолога:", "в логах тысячи строк, но нет чёткого приоритета, кому звонить первым."),
        (0, "Наша цель:", "превратить сухие статусы в конкретные деньги и немедленное действие."),
    ], size=17, gap=16)

    c_top = 2.3
    card_data = [
        ("67,53 €", "платежей под угрозой на демо-снимке", PANTONE_BLACK, PANTONE_GRAY),
        ("3 из 10", "клиентов требуют срочного внимания (Score ≥ 70)", PANTONE_ORANGE, PANTONE_GRAY),
        ("5 дней", "окно спасения в prolong_wait до стирания сервера", PANTONE_298C, PANTONE_NAVY),
    ]
    for val, lbl, val_col, bg_col in card_data:
        rect(slide, 7.8, c_top, 4.6, 1.25, bg_col, radius=True)
        text(slide, 8.1, c_top + 0.12, 4.1, 0.65, val, 38, bold=True, color=val_col, font=HEAD)
        text(slide, 8.1, c_top + 0.72, 4.1, 0.45, lbl, 13, bold=True, color=WHITE if bg_col == PANTONE_NAVY else PANTONE_NAVY, font=BODY)
        c_top += 1.42

    note(slide,
         "[0:18–0:50 | 42 слова]\n\n"
         "«В хостинге обычный биллинг не спасает: когда сервер удалён — удерживать поздно. "
         "Отток нужно перехватывать раньше: когда услугу отключили (suspended) или она ждёт оплаты (prolong_wait). "
         "На нашем снимке под риском 67,53 евро. Система мгновенно выявляет критических клиентов».")

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 3 ─ РЕШЕНИЕ: ДАШБОРД (34 слова | ~25 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, number=3)
    eyebrow(slide, "Решение кейса")
    title(slide, "Три ответа ТЗ — один рабочий экран")

    rows = [
        ("01", "Кому звонить:", "Рейтинг по Risk Score и срочности (до 7 дней). Сортировка и экспорт CSV."),
        ("02", "Почему уходит:", "Причина человеческим языком: «На продление нужно 5,50 €, на балансе 3,00 €»."),
        ("03", "Сколько теряем:", "Точная денежная оценка по ближайшим платежам за услуги с учётом баланса."),
    ]
    top = 2.35
    for number, head, body in rows:
        text(slide, MARGIN, top, 0.85, 0.45, number, 26, bold=True, color=PANTONE_298C, font=HEAD)
        text(slide, MARGIN + 0.9, top - 0.02, 4.5, 0.38, head, 19, bold=True, color=PANTONE_BLACK, font=HEAD)
        text(slide, MARGIN + 0.9, top + 0.4, 4.5, 0.8, body, 14, color=PANTONE_NAVY, font=BODY)
        top += 1.4

    # Крупный чёткий скриншот дашборда справа (1440x920 viewport)
    if DASH_CROP_PATH.exists():
        image(slide, DASH_CROP_PATH, 6.35, 2.25, 6.15, border=True)

    note(slide,
         "[0:50–1:15 | 34 слова]\n\n"
         "«Мы объединили все три ответа кейса на одном экране дашборда:\n"
         "Первое — рейтинг клиентов по уровню риска и срочности продления.\n"
         "Второе — понятная причина фразой, а не абстрактная цифра.\n"
         "Третье — точная денежная оценка по ближайшим платежам».")

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 4 ─ ДЕЙСТВИЕ: ПИСЬМО В 1 КЛИК (32 слова | ~25 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, number=4)
    eyebrow(slide, "Действие и retention")
    title(slide, "От анализа к действию: удержание в 1 клик")

    bullets(slide, MARGIN, 2.35, 6.4, 4.2, [
        (0, "Маркетолог не тратит время на рутину:", "система сама формирует контекст обращения."),
        (0, "7 готовых сценариев удержания:", "от нехватки денег до зависшей оплаты и блокировки."),
        (0, "Умная автоподстановка:", "в письмо подставляются имя, название сервера, сумма доплаты и промокод."),
        (0, "Мгновенное действие:", "копирование текста в один клик или прямая ссылка mailto: для отправки."),
    ], size=17, gap=16)

    # Крупное диалоговое окно письма справа
    if EMAIL_CROP_PATH.exists():
        image(slide, EMAIL_CROP_PATH, 7.85, 2.2, 4.6, border=True)

    note(slide,
         "[1:15–1:40 | 32 слова]\n\n"
         "«Главное — аналитика сразу переходит в действие. По клику на клиента открывается персонализированный драфт письма: "
         "система сама подставляет услугу, сумму к доплате и промокод. Маркетолог удерживает клиента в один клик».")

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 5 ─ МЕТОДОЛОГИЯ И ЧЕСТНОСТЬ (44 слова | ~30-35 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, number=5)
    eyebrow(slide, "Методология и честность")
    title(slide, "Прозрачные правила вместо чёрного ящика")

    text(slide, MARGIN, 2.25, 6.0, 0.35, "7 ПРИЗНАКОВ И ВЕСА (НАСТРАИВАЮТСЯ В ПАНЕЛИ БЕЗ КОДА)", 11, bold=True, color=PANTONE_NAVY, font=HEAD)
    weights = [
        ("Срочность продления", "0,40"), ("Нехватка баланса", "0,25"),
        ("Автопродление OFF", "0,10"), ("Статус prolong / susp", "0,10"),
        ("История неоплат", "0,10"), ("Лояльность / стаж", "0,05"),
    ]
    left, top = MARGIN, 2.65
    for index, (name, weight) in enumerate(weights):
        column, row = index % 2, index // 2
        x = left + column * 3.1
        y = top + row * 0.65
        text(slide, x, y, 2.3, 0.35, name, 13, bold=True, color=PANTONE_BLACK, font=HEAD)
        text(slide, x + 2.3, y, 0.6, 0.35, weight, 14, bold=True, color=PANTONE_NAVY, align=PP_ALIGN.RIGHT, font=HEAD)
        rect(slide, x, y + 0.42, 2.9, 0.015, LINE_COLOR)

    rect(slide, MARGIN, 4.7, 5.8, 1.85, PANTONE_GRAY, radius=True)
    text(slide, MARGIN + 0.25, 4.85, 5.3, 0.3, "РАСЧЁТ ДЕНЕГ ПОД РИСКОМ", 11, bold=True, color=PANTONE_NAVY, font=HEAD)
    text(slide, MARGIN + 0.25, 5.2, 5.3, 0.45, "Потери = P(score) × price × (1 − 0,5 × баланс)", 16, bold=True, font=HEAD, color=PANTONE_BLACK)
    text(slide, MARGIN + 0.25, 5.7, 5.3, 0.75,
         "Считаем от цены продления услуги (price), а не из случайных сумм транзакций. "
         "Баланс гасит риск максимум наполовину: деньги есть, но сервер могут не продлить.", 12, color=PANTONE_NAVY, font=BODY)

    rect(slide, 7.3, 2.25, 5.1, 4.3, PANTONE_NAVY, radius=True)
    text(slide, 7.6, 2.55, 4.5, 0.45, "ПОЧЕМУ НЕ ML?", 22, bold=True, color=PANTONE_298C, font=HEAD)
    bullets(slide, 7.6, 3.1, 4.5, 3.2, [
        (0, "0 меток оттока и 0 истории:", "в данных нет исходов — обучать ML не на чем."),
        (0, "ML на 10 строках — самообман:", "модель просто заучит шум и выдаст ложные цифры."),
        (0, "Полная прозрачность:", "маркетолог понимает каждый балл и меняет веса в UI."),
        (0, "Калибровка без смены кода:", "появится история — модель откалибруется моментально."),
    ], size=13, gap=10, color=WHITE)

    note(slide,
         "[1:40–2:10 | 44 слова]\n\n"
         "«Почему не машинное обучение? В исходных данных нет истории и меток оттока. Обучать ML на десяти строках — это самообман.\n"
         "Мы применили прозрачную модель из семи признаков. Маркетолог может сам менять их веса в интерфейсе, а потери считаются от реального платежа за услугу».")

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 6 ─ ИНЖЕНЕРИЯ И ПРОД-ГОТОВНОСТЬ (35 слов | ~25-30 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, number=6)
    eyebrow(slide, "Инженерия и прод-готовность")
    title(slide, "Готов к бою: одна команда запуска и 449 тестов")

    cards = [
        ("1 команда", "docker compose up\nготов за секунды", PANTONE_298C),
        ("449 тестов", "backend + Playwright e2e\n100% зелёный CI", PANTONE_BLACK),
        ("3,1 сек", "на 10 000 клиентов\np95 чтения 24 мс", PANTONE_BLACK),
        ("Enterprise", "Prometheus /metrics\nSwagger + Keycloak SSO", PANTONE_NAVY),
    ]
    for index, (head, body, col) in enumerate(cards):
        x = MARGIN + index * 2.92
        rect(slide, x, 2.3, 2.65, 1.55, PANTONE_GRAY, radius=True)
        text(slide, x + 0.2, 2.45, 2.35, 0.45, head, 22, bold=True, color=col, font=HEAD)
        text(slide, x + 0.2, 3.0, 2.35, 0.75, body, 12, bold=True, color=PANTONE_NAVY, font=BODY)

    bullets(slide, MARGIN, 4.15, 6.6, 2.6, [
        (0, "Воспроизводимость:", "жюри разворачивает стенд одной строкой из docs/JURY.md."),
        (0, "SQLite WAL:", "высокая скорость, устойчивость к сбоям, данные сохраняются."),
        (0, "Реальное время:", "SSE-стриминг мгновенно обновляет дашборд при смене данных."),
        (0, "Безопасность:", "сессии HttpOnly, защита от перебора PBKDF2, OIDC с PKCE."),
    ], size=14, gap=10)

    image(slide, SHOTS / "11-login-sso.png", 8.0, 4.1, 4.3)

    note(slide,
         "[2:10–2:35 | 35 слов]\n\n"
         "«Сервис полностью готов. Вы можете развернуть и проверить его прямо сейчас одной командой docker compose up. "
         "В проекте 449 бэкенд-тестов и браузерные E2E тесты. База данных оптимизирована под 10 000 клиентов, подключены Swagger, Prometheus и корпоративный SSO».")

    # ─────────────────────────────────────────────────────────────
    # СЛАЙД 7 ─ ФИНАЛ И ПРИГЛАШЕНИЕ К Q&A (18 слов | ~15 сек)
    # ─────────────────────────────────────────────────────────────
    slide = new_slide(prs, number=7, background=PANTONE_GRAY)
    eyebrow(slide, "Итог и проверка")
    title(slide, "ОТТОК · Risk Desk")

    rect(slide, MARGIN, 2.25, 5.9, 4.4, WHITE, line=PANTONE_NAVY, radius=True)
    text(slide, MARGIN + 0.4, 2.5, 5.1, 0.4, "РЕЗУЛЬТАТ", 14, bold=True, color=PANTONE_NAVY, font=HEAD)
    bullets(slide, MARGIN + 0.4, 3.0, 5.1, 3.4, [
        (0, "100% покрытие ТЗ:", "все три вопроса кейса закрыты в одном окне."),
        (0, "Retention в 1 клик:", "персональный драфт письма клиенту с промокодом."),
        (0, "Прогноз оттока во времени:", "факт просрочек и прогноз на 30 дней с CSV."),
        (0, "449 автотестов:", "гарантия надёжности математики и API контрактов."),
        (0, "Готов к интеграции:", "Swagger, Prometheus и Keycloak SSO из коробки."),
    ], size=14, gap=11)

    rect(slide, 7.3, 2.25, 5.1, 4.4, PANTONE_NAVY, radius=True)
    text(slide, 7.6, 2.5, 4.5, 0.45, "ГОТОВЫ К ВОПРОСАМ", 22, bold=True, color=PANTONE_298C, font=HEAD)
    text(slide, 7.6, 2.95, 4.5, 0.35, "Прямая ссылка на GitHub (код, тесты, docs/JURY.md):", 11, color=WHITE, font=BODY)

    rect(slide, 7.6, 3.4, 2.3, 2.3, WHITE, radius=True)
    image(slide, QR_PATH, 7.7, 3.5, 2.1, border=False)

    text(slide, 10.1, 3.45, 2.1, 2.2,
         "СКАН ДЛЯ ЖЮРИ:\n\n"
         "docker compose up\n\n"
         "Swagger API:\n/api/v1/docs\n\n"
         "Prometheus:\n/metrics\n\n"
         "Вход: admin / admin",
         10.5, bold=True, color=WHITE, font=HEAD, line_spacing=1.15)

    text(slide, 7.6, 5.9, 4.5, 0.4, "github.com/Demtory/Hack23.10.26", 12, bold=True, color=PANTONE_298C, font=HEAD)

    note(slide,
         "[2:35–2:50 | 18 слов]\n\n"
         "«Инструкция по запуску — в файле JURY.md. Спасибо за внимание, мы готовы ответить на вопросы и показать работу системы».")

    # --- Слайд 8: панель в один скан
    slide = new_slide(prs, number=8, background=PANTONE_GRAY)
    eyebrow(slide, "Демо-стенд")
    title(slide, "ПАНЕЛЬ В ОДИН СКАН")

    rect(slide, MARGIN, 2.25, 5.2, 4.4, WHITE, line=PANTONE_NAVY, radius=True)
    if DEMO_QR_PATH.exists():
        image(slide, DEMO_QR_PATH, MARGIN + 0.55, 2.5, 3.35, border=False)
    else:
        text(slide, MARGIN + 0.5, 3.6, 4.2, 0.6, "QR не сгенерирован", 14, bold=True, font=HEAD)
    text(slide, MARGIN + 0.4, 5.95, 4.4, 0.6,
         "Наведите камеру — панель откроется\nсразу, без пароля", 12, color=PANTONE_NAVY, font=BODY)

    rect(slide, 6.7, 2.25, 5.7, 4.4, PANTONE_NAVY, radius=True)
    text(slide, 7.0, 2.5, 5.1, 0.4, "ЧТО ПРОВЕРИТЬ ЗА 60 СЕКУНД", 14, bold=True, color=PANTONE_298C, font=HEAD)
    bullets(slide, 7.0, 2.95, 5.1, 3.4, [
        (0, "Сводка:", "16,87 € потерь, 43,91 € под риском, 3 из 10 — высокий."),
        (0, "Прогноз:", "6 истёкших услуг, 1,7 ожидаемых непродлений, 6,88 €."),
        (0, "Клиент 6:", "причины, деньги, готовое письмо маркетолога."),
        (0, "Настройки:", "пресет «Деньги важнее» → 89 → 95 без перезагрузки."),
        (0, "SSO:", "кнопка Keycloak, marketer@example.test."),
    ], size=12.5, gap=9, color=WHITE)

    text(slide, 7.0, 5.95, 5.1, 0.5,
         "Без QR: 193.233.246.179:8000 · admin@example.test / admin123", 10, color=WHITE, font=BODY)

    note(slide,
         "[2:50–3:00 | 15 слов]\n\n"
         "«Вот QR: сканируете — панель открывается сразу, без пароля и Docker. "
         "Это тот же код, что в репозитории, просто уже развёрнутый».")

    prs.save(output_path)
    return output_path


if __name__ == "__main__":
    path = build()
    from pptx import Presentation as P

    deck = P(str(path))
    print(f"Презентация успешно сгенерирована: {path}")
    print(f"Количество слайдов: {len(deck.slides)}")
