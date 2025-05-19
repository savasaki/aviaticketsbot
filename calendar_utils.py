import datetime
from calendar import monthrange
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from utils import t, build_tracking_settings_keyboard
from search import process_selected_dates

MAX_MONTHS_FORWARD = 12

async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    markup = build_calendar_markup(context.user_data['calendar'], lang)
    if update.message:
        await update.message.reply_text(t("choose_dates", lang), reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(t("choose_dates", lang), reply_markup=markup)

def build_calendar_markup(data, lang="ru"):
    now = datetime.datetime.now()
    target_month = now.month + data.get('month_offset', 0)
    target_year = now.year + (target_month - 1) // 12
    target_month = ((target_month - 1) % 12) + 1
    _, days_in_month = monthrange(target_year, target_month)
    keyboard = []
    month_name = t(f"months_{target_month - 1}", lang)
    calendar_title = t("calendar_title", lang, month=month_name, year=target_year)
    keyboard.append([InlineKeyboardButton(calendar_title, callback_data="noop")])
    day_labels = [t(f"weekdays_{i}", lang) for i in range(7)]
    keyboard.append([InlineKeyboardButton(day, callback_data="noop") for day in day_labels])
    first_day_weekday = datetime.date(target_year, target_month, 1).weekday()
    week = [InlineKeyboardButton(" ", callback_data="noop")] * first_day_weekday
    for day in range(1, days_in_month + 1):
        day_str = f"{day:02d}-{target_month:02d}-{target_year}"
        is_selected = day_str in data.get('selected', [])
        label = f"[{day}]" if is_selected else str(day)
        week.append(InlineKeyboardButton(label, callback_data=f"cal:{day_str}"))
        if len(week) == 7:
            keyboard.append(week)
            week = []
    if week:
        week += [InlineKeyboardButton(" ", callback_data="noop")] * (7 - len(week))
        keyboard.append(week)
    nav_buttons = []
    if data.get('month_offset', 0) > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data="prev_month"))
    if data.get('month_offset', 0) < MAX_MONTHS_FORWARD - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data="next_month"))
    keyboard.append(nav_buttons)
    keyboard.append([
        InlineKeyboardButton(t("calendar_done", lang), callback_data="calendar_done"),
        InlineKeyboardButton(t("calendar_clear", lang), callback_data="calendar_clear")
    ])
    return InlineKeyboardMarkup(keyboard)

async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    data = context.user_data.get('calendar')
    if not data:
        await query.edit_message_text(t("calendar_no_route", lang))
        return
    if query.data.startswith("cal:"):
        date = query.data[4:]
        if date in data.get('selected', []):
            data['selected'].remove(date)
        else:
            data['selected'].append(date)
    elif query.data == "next_month":
        data['month_offset'] = data.get('month_offset', 0) + 1
    elif query.data == "prev_month":
        data['month_offset'] = data.get('month_offset', 0) - 1
    elif query.data == "calendar_clear":
        data['selected'] = []
    elif query.data == "calendar_done":
        past_dates = []
        today = datetime.date.today()
        for d in list(data.get('selected', [])):
            try:
                parsed = datetime.datetime.strptime(d, "%d-%m-%Y").date()
                if parsed < today:
                    past_dates.append(d)
            except Exception:
                continue
        if past_dates:
            data['selected'] = [d for d in data['selected'] if d not in past_dates]
            formatted = ", ".join(past_dates)
            combined_text = f"{t('past_date', lang)}: {formatted}\n\n{t('choose_dates', lang)}"
            markup = build_calendar_markup(data, lang)
            await query.edit_message_text(combined_text, reply_markup=markup)
            return
        if context.user_data.get("calendar_mode") == "track":
            context.user_data.setdefault("track", {})
            context.user_data["track"]["selected_dates"] = data.get("selected", [])
            await query.edit_message_text(
                t("track_prompt_dates", lang),
                reply_markup=build_tracking_settings_keyboard(lang)
            )
        else:
            await query.edit_message_text(t("searching_selected_dates", lang))
            await process_selected_dates(update, context)
        return
    markup = build_calendar_markup(data, lang)
    await query.edit_message_reply_markup(reply_markup=markup)
