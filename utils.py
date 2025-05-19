from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import SessionLocal
from models import Currency, Airline, Translation

API_TOKEN = 'Здесь мой апи ключ для телеграм-бота'
TP_API_TOKEN = 'Здесь мой апи ключ авиасейлс'

translations = {
    "ru": {
        "choose_currency": "Выберите валюту:",
        "welcome": "👋 Введите маршрут, например:\n`москва сочи`\nили с датой: `москва сочи 17-05-2025`",
        "invalid_format": "Введите маршрут в формате: город1 город2 [дата, например 12-05-2025]",
        "city_error": "😕 Не удалось распознать один из городов.",
        "date_error": "❌ Неверный формат даты. Используйте дд-мм-гггг.",
        "past_date": "❗ Дата в прошлом. Укажите будущую дату",
        "not_found": "😕 Не удалось найти билеты по этому маршруту.",
        "language_set": "Язык установлен: Русский 🇷🇺",
        "currency_set": "Валюта установлена: {currency}",
        "calendar_title": "📅 {month} {year}",
        "weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        "calendar_done": "✔️ Готово",
        "calendar_clear": "❌ Очистить",
        "calendar_no_dates": "❗ Вы не выбрали ни одной даты.",
        "filters_title": "Выберите фильтры:",
        "choose_dates": "Выберите даты:",
        "track_saved": "✅ Отслеживание сохранено для {n} даты(дат).",
        "track_prompt_dates": "✅ Даты выбраны! Сейчас уточним параметры уведомлений...",
        "track_price_set": "💰 Максимальная цена установлена: {value} {currency}",
        "track_percent_set": "📉 Уведомление при снижении на {value}%",
        "track_price_label": "Цена:",
        "track_percent_label": "Снижение:",
        "positive_number_only": "Введите положительное число.",
        "untrack_button": "❌ Отменить",
        "notification_price_condition": "цена ≤ {price}",
        "notification_percent_condition": "снижение на {percent}%",
        "notification_text": "🔔 Билет *{origin} → {destination}* на {date}\n💰 Цена: {price} {currency}{condition}",
        "calendar_no_route": "Ошибка: нет активного маршрута.",
        "route_header": "Билеты по маршруту:",
        "unknown_currency": "❌ Неизвестная валюта.",
        "buy_button": "Купить билет",
        "multi_passenger_warning": "⚠️ Итоговая цена за нескольких пассажиров может незначительно отличаться при бронировании — зависит от доступных мест.",
        "filter_set": "Фильтр установлен: {passengers} {word}",
        "filter_done": "✔️ Готово",
        "filters_cleared": "Фильтры сброшены ✅",
        "filter_reset": "❌ Сбросить",
        "direct_flights_only": "Только прямые рейсы",
        "moscow_time": "МСК",
        "include_transfers": "Разрешить пересадки",
        "no_history": "История поиска пуста.",
        "direct": "Прямой рейс",
        "with_transfers": "С пересадками",
        "track_confirm_missing": "❗ Укажите хотя бы цену или процент снижения.",
        "track_set_price": "💰 Указать цену",
        "track_set_price_val": "💰 Указать цену ({value})",
        "track_set_percent": "📉 Указать %",
        "track_set_percent_val": "📉 Указать % ({value}%)",
        "track_save": "✅ Сохранить",
        "track_cancel": "❌ Отмена",
        "tracking_parameters_prompt": "✅ Принято! Сейчас уточним параметры уведомлений...",
        "feedback_thanks": "✅ Спасибо за ваш отзыв!",
        "no_active_tracks": "У вас нет активных отслеживаний.",
        "track_cancelled": "❌ Отслеживание отменено.",
        "no_all_tracks": "У вас пока не было маршрутов отслеживания.",
        "untrack_not_found": "⚠️ Уже отменено или не найдено.",
        "transfers_selected": "Пересадки",
        "feedback_prompt": "✍️ Пожалуйста, напишите свой отзыв одним сообщением:",
        "user_not_found": "Ошибка: пользователь не найден.",
        "untrack_cancelled": "❌ Отслеживание отменено.",
        "notification_error": "❗ Ошибка при отправке уведомления: {error}",
        "status_active": "✅ Активно",
        "track_start_prompt": "👋 Введите маршрут отслеживания, например:\n`москва сочи`\nили с датой: `москва сочи 17-05-2025`",
        "stop_tracking": "Удалить отслеживание",
        "status_cancelled": "❌ Отменено",
        "history_user_not_found": "❌ Пользователь не найден.",
        "track_enter_price": "Введите максимальную цену (например: 7000):",
        "track_enter_percent": "Введите процент снижения цены (например: 15):",
        "no_direct_but_with_transfers": "✈️ Билеты без пересадок не найдены, но есть с пересадками:",
        "searching_selected_dates": "🔍 Поиск по выбранным датам...",
        "calendar_no_route": "Ошибка: нет активного маршрута.",
        "months": ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
           "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
        "help_text": "ℹ️ *Команды бота:*\n"
                "/start — начать заново и выбрать язык\n"
                "/lang — сменить язык\n"
                "/currency — выбрать валюту\n"
                "/filters — настроить фильтры\n"
                "/reset_filters — сбросить фильтры к значениям по умолчанию\n"
                "/history — история поиска\n"
                "/track — отслеживать маршрут\n"
                "/mytracks — мои активные маршруты\n"
                "/alltracks — все отслеживания\n"
                "/feedback — оставить отзыв\n"
                "/help — показать это сообщение\n\n"
                "*Введите маршрут в формате:*\n"
                "`город1 город2 \\[дата\\]`\n"
                "Например:\n"
                "`москва сочи` — появится календарь для выбора дат\n"
                "`москва сочи 12-06-2025` — будет найдено на указанную дату."
    },
    "en": {
        "choose_currency": "Choose a currency:",
        "welcome": "👋 Enter a route like:\n`moscow sochi`\nor with date: `moscow sochi 17-05-2025`",
        "invalid_format": "Enter route in format: city1 city2 [date, e.g. 12-05-2025]",
        "city_error": "😕 One of the cities was not recognized.",
        "date_error": "❌ Invalid date format. Use dd-mm-yyyy.",
        "past_date": "❗ The date is in the past. Choose a future one",
        "not_found": "😕 No tickets found on this route.",
        "language_set": "Language set: English 🇬🇧",
        "user_not_found": "❌ User not found.",
        "no_active_tracks": "You have no active tracking routes.",
        "currency_set": "Currency set to: {currency}",
        "calendar_title": "📅 {month} {year}",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "calendar_done": "✔️ Done",
        "calendar_clear": "❌ Clear",
        "track_cancelled": "❌ Tracking cancelled.",
        "positive_number_only": "Please enter a positive number.",
        "calendar_no_dates": "❗ You haven't selected any dates.",
        "choose_dates": "Select dates:",
        "route_header": "Tickets for route:",
        "track_enter_price": "Enter max price (e.g. 7000):",
        "track_enter_percent": "Enter price drop percent (e.g. 15):",
        "track_saved": "✅ Tracking saved for {n} date(s).",
        "no_all_tracks": "You haven't tracked any routes yet.",
        "buy_button": "Buy ticket",
        "filters_title": "Choose filters:",
        "track_start_prompt": "👋 Enter a tracking route, e.g.:\n`moscow sochi`\nor with date: `moscow sochi 17-05-2025`",
        "stop_tracking": "Stop tracking",
        "track_confirm_missing": "❗ Please set at least a price or a percentage drop.",
        "untrack_not_found": "⚠️ Already cancelled or not found.",
        "feedback_prompt": "✍️ Please type your feedback in one message:",
        "moscow_time": "MSK",
        "tracking_parameters_prompt": "✅ Got it! Now let's configure notification settings...",
        "feedback_thanks": "✅ Thank you for your feedback!",
        "track_prompt_dates": "✅ Dates selected! Now let's configure notification settings...",
        "track_price_set": "💰 Max price set: {value} {currency}",
        "track_percent_set": "📉 Will notify if price drops by {value}%",
        "track_price_label": "Price:",
        "track_percent_label": "Drop:",
        "untrack_button": "❌ Cancel",
        "notification_price_condition": "price ≤ {price}",
        "notification_percent_condition": "{percent}% drop",
        "notification_text": "🔔 Ticket *{origin} → {destination}* on {date}\n💰 Price: {price} {currency}{condition}",
        "unknown_currency": "❌ Unknown currency.",
        "no_history": "Search history is empty.",
        "untrack_cancelled": "❌ Tracking cancelled.",
        "notification_error": "❗ Error sending notification: {error}",
        "status_active": "✅ Active",
        "status_cancelled": "❌ Cancelled",
        "history_user_not_found": "❌ User not found.",
        "direct": "Direct flight",
        "with_transfers": "With transfers",
        "multi_passenger_warning": "⚠️ The total price for multiple passengers is approximate and may slightly vary depending on seat availability.",
        "filter_set": "Filter set: {passengers} {word}",
        "filter_done": "✔️ Done",
        "filters_cleared": "Filters have been reset ✅",
        "filter_reset": "❌ Reset",
        "direct_flights_only": "Direct flights only",
        "include_transfers": "Include transfers",
        "track_set_price": "💰 Set price",
        "track_set_price_val": "💰 Set price ({value})",
        "track_set_percent": "📉 Set % drop",
        "track_set_percent_val": "📉 Set % drop ({value}%)",
        "track_save": "✅ Save",
        "track_cancel": "❌ Cancel",
        "transfers_selected": "Transfers",
        "no_direct_but_with_transfers": "✈️ No direct flights found, but some options with transfers are available:",
        "searching_selected_dates": "🔍 Searching selected dates...",
        "calendar_no_route": "Error: no active route selected.",
        "months": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
        "help_text": "ℹ️ *Bot commands:*\n"
                "/start — restart and select language\n"
                "/lang — change language\n"
                "/currency — choose currency\n"
                "/filters — configure filters\n"
                "/reset\\_filters — reset filters to default values\n"
                "/history — search history\n"
                "/track — track a route\n"
                "/mytracks — my tracked routes\n"
                "/alltracks — all tracked routes\n"
                "/feedback — leave feedback\n"
                "/help — show this message\n\n"
                "*Enter the route in the format:*\n"
                "`city1 city2 \\[date\\]`\n"
                "For example:\n"
                "`moscow sochi` — calendar will appear for selecting dates\n"
                "`moscow sochi 12-06-2025` — search will run for that date."
    }
}

translation_cache = {}

def t(key, lang="ru", **kwargs):
    cached = translation_cache.get((key, lang))
    if cached:
        return cached.format(**kwargs)
    session = SessionLocal()
    entry = session.query(Translation).filter_by(key=key, lang=lang).first()
    session.close()
    if entry:
        translation_cache[(key, lang)] = entry.value
        return entry.value.format(**kwargs)
    fallback = translations.get(lang, {}).get(key, key)
    translation_cache[(key, lang)] = fallback
    return fallback.format(**kwargs)

def plural_passenger(count, lang):
    if lang == "ru":
        if count % 10 == 1 and count % 100 != 11:
            return "пассажир"
        elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
            return "пассажира"
        else:
            return "пассажиров"
    return "passenger" if count == 1 else "passengers"

def fill_currencies():
    session = SessionLocal()
    currencies = [
        {"code": "RUB", "name": "Russian Ruble", "symbol": "₽", "flag": "🇷🇺"},
        {"code": "USD", "name": "US Dollar", "symbol": "$", "flag": "🇺🇸"},
        {"code": "EUR", "name": "Euro", "symbol": "€", "flag": "🇪🇺"},
        {"code": "GBP", "name": "British Pound", "symbol": "£", "flag": "🇬🇧"},
        {"code": "KZT", "name": "Kazakh Tenge", "symbol": "₸", "flag": "🇰🇿"},
        {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥", "flag": "🇨🇳"},
    ]
    for c in currencies:
        if not session.query(Currency).filter_by(code=c["code"]).first():
            session.add(Currency(**c))
    session.commit()
    session.close()

def fill_airlines():
    session = SessionLocal()
    airlines = [
        {"code": "DP", "name_ru": "Победа", "name_en": "Pobeda"},
        {"code": "SU", "name_ru": "Аэрофлот", "name_en": "Aeroflot"},
        {"code": "S7", "name_ru": "S7 Airlines", "name_en": "S7 Airlines"},
        {"code": "UT", "name_ru": "ЮТэйр", "name_en": "UTair"},
        {"code": "U6", "name_ru": "Уральские авиалинии", "name_en": "Ural Airlines"},
    ]
    for a in airlines:
        if not session.query(Airline).filter_by(code=a["code"]).first():
            session.add(Airline(**a))
    session.commit()
    session.close()

def fill_translations():
    session = SessionLocal()
    for lang, entries in translations.items():
        for key, value in entries.items():
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    compound_key = f"{key}_{idx}"
                    if not session.query(Translation).filter_by(key=compound_key, lang=lang).first():
                        session.add(Translation(key=compound_key, lang=lang, value=item))
            else:
                if not session.query(Translation).filter_by(key=key, lang=lang).first():
                    session.add(Translation(key=key, lang=lang, value=value))
    session.commit()
    session.close()

def get_currency_flag(code: str) -> str:
    session = SessionLocal()
    currency = session.query(Currency).filter_by(code=code.upper()).first()
    session.close()
    return currency.flag if currency else ""

def build_currency_inline_keyboard():
    session = SessionLocal()
    currencies = session.query(Currency).all()
    session.close()
    keyboard = []
    row = []
    for i, c in enumerate(currencies, start=1):
        button = InlineKeyboardButton(
            text=f"{c.flag} {c.code} — {c.name} ({c.symbol})",
            callback_data=f"currency:{c.code}"
        )
        row.append(button)
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def build_filter_markup(context) -> InlineKeyboardMarkup:
    lang = context.user_data.get("lang", "ru")
    filters = context.user_data.setdefault("filters", {})
    passengers = filters.get("passengers", 1)
    direct = filters.get("direct", None)
    if direct is True:
        direct_label = t("direct_flights_only", lang)
    else:
        direct_label = "✈️ ✅ " + t("include_transfers", lang)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="passenger_minus"),
            InlineKeyboardButton(f"👥 {passengers} {plural_passenger(passengers, lang)}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="passenger_plus")
        ],
        [InlineKeyboardButton(f"✈️ {direct_label}", callback_data="toggle_direct")],
        [
            InlineKeyboardButton(t("filter_done", lang), callback_data="filters_done"),
            InlineKeyboardButton(t("filter_reset", lang), callback_data="filters_reset")
        ]
    ])

def build_tracking_settings_keyboard(lang="ru", price=None, percent=None) -> InlineKeyboardMarkup:
    price_label = t("track_set_price_val", lang, value=price) if price is not None else t("track_set_price", lang)
    percent_label = t("track_set_percent_val", lang, value=percent) if percent is not None else t("track_set_percent", lang)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(price_label, callback_data="track_price"),
            InlineKeyboardButton(percent_label, callback_data="track_percent"),
        ],
        [
            InlineKeyboardButton(t("track_save", lang), callback_data="track_confirm"),
            InlineKeyboardButton(t("track_cancel", lang), callback_data="track_cancel"),
        ]
    ])
