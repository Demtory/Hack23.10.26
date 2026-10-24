"""Сборка питч-деки «ОТТОК · Risk Desk» (python-pptx).

Запуск:
    python build_pitch.py            # создаст risk-desk-pitch.pptx рядом
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
OUT = Path(__file__).resolve().parent / "risk-desk-pitch.pptx"

BG = RGBColor(0xF4, 0xF4, 0xF4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x00, 0x00, 0x00)
MUTED = RGBColor(0x18, 0x2D, 0x48)
ACCENT = RGBColor(0x4C, 0xC6, 0xF1)
LINE = RGBColor(0xDD, 0xE2, 0xEA)
HIGH = RGBColor(0xB4, 0x23, 0x18)

HEAD = "Exo 2"
BODY = "Inter"

W, H = 13.333, 7.5
MARGIN = 0.9


def rgb_text(box, value, size, *, bold=False, color=INK, font=BODY, align=PP_ALIGN.LEFT,
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


def bullets(slide, left, top, width, height, items, *, size=15, gap=10, color=INK):
    """items: список (уровень, текст); уровень 0 — с маркером, 1 — подпункт."""
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for index, (level, value) in enumerate(items):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.line_spacing = 1.3
        paragraph.space_after = Pt(gap)
        prefix = "—  " if level == 0 else "·  "
        _hanging_indent(paragraph, level)
        run = paragraph.add_run()
        run.text = prefix + value
        run.font.size = Pt(size if level == 0 else size - 2)
        run.font.color.rgb = color if level == 0 else MUTED
        run.font.name = BODY
        if level == 1:
            paragraph.level = 1
    return box


def _hanging_indent(paragraph, level: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    left = 0.0 if level == 0 else 0.28
    p_pr.set("marL", str(int(Inches(left + 0.3))))
    p_pr.set("indent", str(int(-Inches(0.3))))


def rect(slide, left, top, width, height, color, *, line=None, radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    sp_pr = shape._element.spPr
    if sp_pr.find(qn("a:effectLst")) is None:
        sp_pr.append(sp_pr.makeelement(qn("a:effectLst"), {}))
    if radius:
        shape.adjustments[0] = 0.08
    return shape


def new_slide(prs, *, background=WHITE, footer=True, number=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = background
    if footer:
        rect(slide, MARGIN, 7.02, W - 2 * MARGIN, 0.01, LINE)
        text(slide, MARGIN, 7.1, 6, 0.3, "ОТТОК · Risk Desk", 9, color=MUTED, font=HEAD)
        if number is not None:
            text(slide, W - MARGIN - 0.6, 7.1, 0.6, 0.3, f"{number:02d}", 9, color=MUTED,
                 align=PP_ALIGN.RIGHT, font=HEAD)
    return slide


def eyebrow(slide, value):
    text(slide, MARGIN, 0.55, 8, 0.3, value.upper(), 10, bold=True, color=MUTED, font=BODY)


def title(slide, value, *, size=32, top=0.95, width=11.4):
    text(slide, MARGIN, top, width, 1.1, value, size, bold=True, font=HEAD)
    rect(slide, MARGIN, top + (1.0 if size <= 32 else 1.2), 0.9, 0.06, ACCENT)


def image(slide, path, left, top, width, *, height=None, border=True):
    kwargs = {"width": Inches(width)}
    if height is not None:
        kwargs["height"] = Inches(height)
    picture = slide.shapes.add_picture(str(path), Inches(left), Inches(top), **kwargs)
    if border:
        picture.line.color.rgb = LINE
        picture.line.width = Pt(1)
    return picture


def badge(slide, left, top, width, value, color=ACCENT):
    rect(slide, left, top, width, 0.42, color, radius=True)
    text(slide, left + 0.16, top + 0.1, width - 0.3, 0.3, value, 11, bold=True, font=BODY)


def note(slide, value):
    slide.notes_slide.notes_text_frame.text = value


def build() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # 1 ─ титул
    slide = new_slide(prs, background=BG, footer=False)
    rect(slide, 0, 0, 0.28, H, ACCENT)
    text(slide, MARGIN + 0.2, 1.5, 10, 0.4, "ХАКАТОН РНД · УРОВЕНЬ MIDDLE", 12, bold=True, color=MUTED)
    text(slide, MARGIN + 0.2, 2.1, 11, 1.6, "ОТТОК · Risk Desk", 54, bold=True, font=HEAD)
    text(slide, MARGIN + 0.2, 3.55, 10.5, 0.9, "Кому звонить сегодня — и что ему сказать", 24, color=MUTED)
    rect(slide, MARGIN + 0.2, 4.75, 1.4, 0.07, ACCENT)
    text(slide, MARGIN + 0.2, 5.05, 11, 0.4,
         "Панель маркетолога: приоритет клиентов, причины риска и деньги под угрозой", 14, color=MUTED)
    text(slide, MARGIN + 0.2, 6.55, 11, 0.35,
         "FastAPI · React · SQLite · один Docker-образ · 441 тест · CI", 11, color=MUTED, font=BODY)
    note(slide, "30 секунд: кто мы, что покажем. Дальше — проблема, решение, как считаем, что уже работает.")

    # 2 ─ проблема
    slide = new_slide(prs, number=2)
    eyebrow(slide, "Проблема")
    title(slide, "Данные есть, приоритета нет")
    bullets(slide, MARGIN, 2.45, 6.6, 3.6, [
        (0, "Маркетолог видит статусы услуг, но не знает, кто из клиентов уйдёт первым"),
        (0, "В данных нет истории статусов и дат удаления — обучать ML не на чем"),
        (0, "Каждое непродление — прямые деньги: в демо-снимке 67,53 € платежей под риском"),
        (0, "Отчёт «вот таблица» не отвечает на вопрос «что делать сейчас»"),
    ], size=16, gap=14)
    card = rect(slide, 7.9, 2.45, 4.5, 3.35, BG, radius=True)
    text(slide, 8.2, 2.72, 3.9, 0.35, "ДЕМО-СНИМОК, 10 КЛИЕНТОВ", 10, bold=True, color=MUTED)
    text(slide, 8.2, 3.05, 3.9, 0.9, "67,53 €", 40, bold=True, font=HEAD)
    text(slide, 8.2, 3.85, 3.9, 0.4, "платежей под риском", 12, color=MUTED)
    text(slide, 8.2, 4.45, 3.9, 0.9, "3 из 10 — высокий риск\n21,56 € — ожидаемые потери", 12, color=INK)
    note(slide, "Подчеркнуть: проблема не в отсутствии данных, а в отсутствии приоритета и действия.")

    # 3 ─ решение: три вопроса
    slide = new_slide(prs, number=3)
    eyebrow(slide, "Решение")
    title(slide, "Три вопроса — три ответа в одном экране")
    rows = [
        ("01", "Кому звонить", "Рейтинг с фильтрами по уровню и срочности, сортировка и экспорт CSV"),
        ("02", "Почему риск", "Причина одной фразой, раскрываемые факты, вклад каждого признака"),
        ("03", "Сколько теряем", "Деньги по ближайшим платежам и готовое письмо клиенту"),
    ]
    top = 2.35
    for number, head, body in rows:
        text(slide, MARGIN, top, 0.8, 0.5, number, 22, bold=True, color=ACCENT, font=HEAD)
        text(slide, MARGIN + 0.85, top - 0.03, 3.3, 0.4, head, 17, bold=True, font=HEAD)
        text(slide, MARGIN + 0.85, top + 0.4, 4.6, 0.7, body, 12, color=MUTED)
        top += 1.35
    image(slide, SHOTS / "02-overview-1440.png", 6.55, 2.15, 5.85)
    note(slide, "Один экран закрывает все три вопроса кейса. Показать, что это не набор графиков, а маршрут к действию.")

    # 4 ─ модель
    slide = new_slide(prs, number=4)
    eyebrow(slide, "Модель")
    title(slide, "Прозрачные правила вместо чёрного ящика")
    text(slide, MARGIN, 2.3, 6.4, 0.35, "ШЕСТЬ ПРИЗНАКОВ И ВЕСА (МЕНЯЮТСЯ В ПАНЕЛИ)", 10, bold=True, color=MUTED)
    weights = [
        ("Срочность продления", "0,40"), ("Нехватка денег", "0,25"),
        ("Автопродление off", "0,10"), ("Статус услуги", "0,10"),
        ("История неоплат", "0,10"), ("Лояльность", "0,05"),
    ]
    left, top = MARGIN, 2.65
    for index, (name, weight) in enumerate(weights):
        column, row = index % 2, index // 2
        x = left + column * 3.25
        y = top + row * 0.62
        text(slide, x, y, 2.45, 0.3, name, 12, color=INK)
        text(slide, x + 2.45, y, 0.6, 0.3, weight, 12, bold=True, color=MUTED, align=PP_ALIGN.RIGHT)
        rect(slide, x, y + 0.42, 3.05, 0.01, LINE)
    text(slide, MARGIN, 4.55, 6.2, 0.9, "Score 0–100 · уровни 40/70 · prolong_wait и устаревшие статусы\nполучают минимум 70, blocked — 60", 12, color=MUTED)
    box = rect(slide, 7.35, 2.35, 5.05, 3.9, BG, radius=True)
    text(slide, 7.65, 2.6, 4.5, 0.35, "ДЕНЬГИ", 10, bold=True, color=MUTED)
    text(slide, 7.65, 3.0, 4.5, 0.6, "P(score) × price × (1 − 0,5 × покрытие)", 15, bold=True, font=HEAD)
    text(slide, 7.65, 3.7, 4.45, 2.4,
         "Считаем от ближайшего платежа, а не от суммы транзакции. "
         "Баланс снижает потерю максимум наполовину: деньги отложены, но клиент всё равно может уйти.\n\n"
         "Пример: 5,50 € через 2 дня, баланс 3,00 € → score 89, ожидаемые потери 6,44 €.",
         11.5, color=INK, line_spacing=1.3)
    note(slide, "Ключевая мысль: решение объяснимо и настраивается без кода. Формула денег — на слайде, чтобы не выглядеть магией.")

    # 5 ─ честность
    slide = new_slide(prs, number=5)
    eyebrow(slide, "Честность")
    title(slide, "Почему не ML — и почему это сильная сторона")
    bullets(slide, MARGIN, 2.4, 6.3, 3.9, [
        (0, "В данных нет меток «ушёл / остался» и истории статусов"),
        (1, "обучать не на чем: 10 записей дадут подгонку, а не прогноз"),
        (0, "Score — экспертная шкала, а не статистическая вероятность"),
        (1, "P(score) — соглашение, оно подписано и в интерфейсе, и в API"),
        (0, "Зато причины видно, веса можно оспорить и изменить в панели"),
        (0, "Когда появятся исходы, шкала калибруется — архитектура не меняется"),
    ], size=15, gap=11)
    rect(slide, 7.7, 2.4, 4.7, 3.6, ACCENT, radius=True)
    text(slide, 8.0, 2.8, 4.1, 0.4, "ЧЕГО МЫ НЕ ДЕЛАЕМ", 10, bold=True, color=INK)
    bullets(slide, 8.0, 3.2, 4.1, 2.5, [
        (0, "не обещаем точность прогноза"),
        (0, "не называем деньги гарантированным убытком"),
        (0, "не показываем тренды, которых нет в данных"),
    ], size=13, gap=10)
    note(slide, "Это любимый вопрос жюри. Отвечаем прямо: данных для ML нет, и мы не притворяемся.")

    # 6 ─ действие
    slide = new_slide(prs, number=6)
    eyebrow(slide, "Действие")
    title(slide, "Из анализа — в письмо клиенту")
    bullets(slide, MARGIN, 2.35, 4.45, 3.9, [
        (0, "Черновик письма под 7 ситуаций — от нехватки денег до блокировки"),
        (0, "Суммы, сроки и услуга подставляются из расчёта"),
        (0, "Копирование и mailto: — отправляет маркетолог"),
        (0, "Веса меняются без перезагрузки, метрики сходятся с UI"),
    ], size=14, gap=12)
    image(slide, SHOTS / "04-customer-card.png", 5.55, 1.95, 3.3)
    image(slide, SHOTS / "10-email-dialog.png", 9.0, 2.35, 3.3)
    note(slide, "Показать живой путь: клиент 6 → причина → письмо. Это то, чего нет у типичного дашборда.")

    # 7 ─ прогноз
    slide = new_slide(prs, number=7)
    eyebrow(slide, "Прогноз")
    title(slide, "Когда наступит отток: факт и прогноз разделены")
    image(slide, SHOTS / "12-forecast.png", MARGIN, 2.3, 8.3)
    bullets(slide, 9.55, 2.35, 3.1, 3.8, [
        (0, "Слева — факт по снимку: срок истёк, услуга не продлена"),
        (0, "Справа — прогноз: срок истекает, вероятность взята из score"),
        (0, "Исторических удалений нет: в данных нет даты удаления — говорим прямо"),
    ], size=12, gap=12)
    note(slide, "Бонусный пункт кейса: график оттока. Показать, что факт и прогноз не смешаны, и честно сказать про отсутствие дат удаления.")

    # 8 ─ прод-готовность
    slide = new_slide(prs, number=8)
    eyebrow(slide, "Инженерия")
    title(slide, "Одна команда — и проверки машиной")
    cards = [
        ("1 команда", "docker compose up --build\n12 секунд до healthz"),
        ("441 тест", "backend + генератор данных\n9 e2e в браузере"),
        ("CI", "pytest, сборка, OpenAPI,\ncompose и docker build"),
        ("SSO", "OIDC + PKCE, Keycloak\nв отдельном оверлее"),
    ]
    for index, (head, body) in enumerate(cards):
        x = MARGIN + index * 2.92
        rect(slide, x, 2.45, 2.62, 1.55, BG, radius=True)
        text(slide, x + 0.2, 2.65, 2.35, 0.4, head, 20, bold=True, font=HEAD)
        text(slide, x + 0.2, 3.15, 2.35, 0.75, body, 10.5, color=MUTED)
    bullets(slide, MARGIN, 4.35, 6.4, 2.3, [
        (0, "10 000 клиентов: пересчёт 3,1 с, список p95 24 мс"),
        (0, "Prometheus /metrics и Swagger /api/v1/docs"),
        (0, "Настройки и снимок переживают перезапуск"),
    ], size=14, gap=10)
    image(slide, SHOTS / "11-login-sso.png", 8.2, 4.15, 4.05)
    note(slide, "Здесь добиваем инженерные критерии: Docker, тесты, метрики, auth, документация.")

    # 9 ─ ограничения и финал
    slide = new_slide(prs, number=9, background=BG)
    eyebrow(slide, "Границы и следующий шаг")
    title(slide, "Что мы знаем про свои ограничения")
    bullets(slide, MARGIN, 2.4, 5.9, 3.9, [
        (0, "10 клиентов в демо-данных — для «топ-клиентов» мало"),
        (0, "Нет истории статусов: прогноза оттока во времени нет"),
        (0, "Деньги — оценка ближайших платежей, не месячная выручка"),
        (0, "Дальше: накопление снапшотов, калибровка на исходах, Grafana"),
    ], size=15, gap=13)
    rect(slide, 7.0, 2.4, 5.4, 3.6, ACCENT, radius=True)
    text(slide, 7.35, 2.75, 4.75, 1.2, "Риск превращается\nв действие", 30, bold=True, font=HEAD)
    text(slide, 7.35, 4.15, 4.75, 1.4,
         "Репозиторий и инструкция для запуска\nв docs/JURY.md — три минуты до панели.", 12, color=INK)
    note(slide, "Финал: честно про ограничения и одна фраза-позиционирование. Дальше вопросы.")

    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    from pptx import Presentation as P

    deck = P(str(path))
    print(f"готово: {path}")
    print(f"слайдов: {len(deck.slides)}")
