import logging
import nest_asyncio
import asyncio
import datetime
import pytz
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from db import init_db, SessionLocal
from models import User, Currency, Feedback, SearchHistory
from sqlalchemy.orm import joinedload
from utils import t, plural_passenger, build_filter_markup, build_currency_inline_keyboard, build_tracking_settings_keyboard, API_TOKEN, fill_airlines, fill_currencies, fill_translations
from search import get_iata_code, get_ticket_price, save_search_and_results
from tracking import track_command, track_callback, my_tracks, all_tracks, untrack_callback, check_prices_for_all
from calendar_utils import calendar_callback, show_calendar

logging.basicConfig(level=logging.INFO)
nest_asyncio.apply()

async def reply(update: Update, text: str, **kwargs):
    if update.message:
        return await update.message.reply_text(text, **kwargs)
    elif update.callback_query:
        return await update.callback_query.message.reply_text(text, **kwargs)

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, "Выберите язык / Choose your language:", reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Русский 🇷🇺", callback_data="lang:ru"),
            InlineKeyboardButton("English 🇬🇧", callback_data="lang:en")
        ]
    ]))

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split(":")[1]
    context.user_data["lang"] = lang
    await query.edit_message_text(t("language_set", lang))
    session = SessionLocal()
    telegram_id = query.from_user.id
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(
            telegram_id=telegram_id,
            language=lang,
            currency="RUB" if lang == "ru" else "USD"
        )
        session.add(user)
    else:
        user.language = lang
    session.commit()
    session.close()
    await choose_currency(update, context)

async def choose_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await reply(update, t("choose_currency", lang), reply_markup=build_currency_inline_keyboard())

async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    if query.data.startswith("currency:"):
        code = query.data.split(":")[1].upper()
        session = SessionLocal()
        currency = session.query(Currency).filter_by(code=code).first()
        session.close()
        if not currency:
            await query.message.reply_text(t("unknown_currency", lang))
            return
        session = SessionLocal()
        telegram_id = query.from_user.id
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.currency = currency.code
        else:
            user = User(
                telegram_id=telegram_id,
                language=lang,
                currency=currency.code
            )
            session.add(user)
        session.commit()
        session.close()
        context.user_data["currency"] = currency.code
        await query.edit_message_text(
            t("currency_set", lang, currency=f"{currency.code} {currency.flag} ({currency.symbol})")
        )
        filters_data = context.user_data.setdefault('filters', {})
        filters_data.setdefault('passengers', 1)
        filters_data.setdefault('direct', False)
        await query.message.reply_text(
            t("filters_title", lang),
            reply_markup=build_filter_markup(context)
        )

async def filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filters_data = context.user_data.setdefault('filters', {})
    filters_data.setdefault('passengers', 1)
    filters_data.setdefault('direct', False)
    lang = context.user_data.get("lang", "ru")
    await reply(update, t("filters_title", lang), reply_markup=build_filter_markup(context))

async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    filters_data = context.user_data.setdefault("filters", {})
    passengers = filters_data.get("passengers", 1)
    if query.data in ("passenger_plus", "passenger_minus"):
        delta = 1 if query.data == "passenger_plus" else -1
        filters_data["passengers"] = max(1, min(9, passengers + delta))
        markup = build_filter_markup(context)
        await query.edit_message_reply_markup(reply_markup=markup)
        return
    elif query.data == "toggle_direct":
        current = filters_data.get("direct", False)
        filters_data["direct"] = not current
        markup = build_filter_markup(context)
        await query.edit_message_reply_markup(reply_markup=markup)
        return
    elif query.data == "filters_reset":
        filters_data.clear()
        filters_data["passengers"] = 1
        filters_data["direct"] = False
        markup = build_filter_markup(context)
        await query.edit_message_reply_markup(reply_markup=markup)
        await query.answer(t("filters_cleared", lang), show_alert=False)
        return
    elif query.data == "filters_done":
        direct = filters_data.get("direct", False)
        passengers = filters_data.get("passengers", 1)
        direct_text = t("direct_flights_only", lang) if direct else t("include_transfers", lang)
        await query.edit_message_text(
            f"{t('filter_set', lang, passengers=passengers, word=plural_passenger(passengers, lang))}\n"
            f"{t('transfers_selected', lang)}: {direct_text}"
        )
        await query.message.reply_text(
            t("welcome", lang),
            parse_mode='Markdown',
        )
        return

async def reset_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['filters'] = {
        'passengers': 1,
        'direct': False
    }
    lang = context.user_data.get("lang", "ru")
    await update.message.reply_text(t("filters_cleared", lang))
    await reply(update, t("filters_title", lang), reply_markup=build_filter_markup(context))

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    context.user_data["awaiting_feedback"] = True
    await update.message.reply_text(t("feedback_prompt", lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await reply(update, t("help_text", lang))

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    telegram_id = update.effective_user.id
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        await reply(update, t("history_user_not_found", lang))
        session.close()
        return
    user_history = (
        session.query(SearchHistory)
        .options(joinedload(SearchHistory.results))
        .filter_by(user_id=user.id)
        .order_by(SearchHistory.search_time.desc())
        .limit(5)
        .all()
    )
    if not user_history:
        await reply(update, t("no_history", lang))
        session.close()
        return
    history_messages = []
    for entry in user_history:
        moscow_tz = pytz.timezone("Europe/Moscow")
        utc_time = entry.search_time.replace(tzinfo=pytz.UTC)
        moscow_time = utc_time.astimezone(moscow_tz)
        msg = (f"📅 {moscow_time.strftime('%d.%m.%Y %H:%M')} ({t('moscow_time', lang)})\n"
               f"✈ {entry.origin_city} → {entry.destination_city} ({datetime.datetime.strptime(entry.depart_date, '%Y-%m-%d').strftime('%d.%m.%Y')})\n"
               f"👥 {entry.passengers} {plural_passenger(entry.passengers, lang)}")
        if entry.results:
            best = sorted(entry.results, key=lambda r: r.price)[0]
            total_price = best.price * entry.passengers
            msg += (f"\n💰 {total_price} {best.currency} | {best.airline_code} | "
                    f"{t('direct', lang) if entry.direct_only else t('with_transfers', lang)}")
        history_messages.append(msg)
    await reply(update, "\n\n".join(history_messages))
    session.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    if context.user_data.get("track_mode"):
        text = update.message.text.strip().lower()
        if any(code in text.upper() for code in ["RUB", "USD", "EUR", "GBP", "KZT", "CNY"]) and "—" in text:
            return
        parts = text.split()
        if len(parts) not in [2, 3]:
            await update.message.reply_text(t("invalid_format", lang))
            return
        origin_city, dest_city = parts[0], parts[1]
        date_str = parts[2] if len(parts) == 3 else None
        context.user_data["track"] = {
            "origin": origin_city,
            "destination": dest_city,
            "date": date_str,
            "selected_dates": []
        }
        if date_str:
            try:
                parsed_date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
                if parsed_date.date() < datetime.date.today():
                    await update.message.reply_text(f"{t('past_date', lang)}: {parsed_date.strftime('%d-%m-%Y')}")
                    return
            except ValueError:
                await update.message.reply_text(t("date_error", lang))
                return
            await update.message.reply_text(
                t("tracking_parameters_prompt", lang),
                reply_markup=build_tracking_settings_keyboard(lang)
            )
        else:
            context.user_data['calendar'] = {
                'origin_city': origin_city,
                'dest_city': dest_city,
                'selected': [],
                'month_offset': 0
            }
            context.user_data['calendar_mode'] = "track"
            await show_calendar(update, context)
        context.user_data["track_mode"] = False
        return
    if context.user_data.get("track_awaiting") in ("price", "percent"):
        text = update.message.text.strip()
        try:
            value = int(text)
            if value <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(t("positive_number_only", lang))
            return
        track_data = context.user_data.setdefault("track", {})
        if context.user_data["track_awaiting"] == "price":
            track_data["price"] = value
        else:
            track_data["percent"] = value
        context.user_data["track_awaiting"] = None
        price_val = track_data.get("price")
        percent_val = track_data.get("percent")
        summary_lines = []
        if price_val is not None:
            summary_lines.append(t("track_price_set", lang, value=price_val, currency=context.user_data.get("currency", "RUB")))
        if percent_val is not None:
            summary_lines.append(t("track_percent_set", lang, value=percent_val))
        reply_text = "\n".join(summary_lines)
        await update.message.reply_text(reply_text, reply_markup=build_tracking_settings_keyboard(lang, price_val, percent_val))
        return
    if context.user_data.get("awaiting_feedback"):
        session = SessionLocal()
        telegram_id = update.effective_user.id
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            fb = Feedback(user_id=user.id, message=update.message.text)
            session.add(fb)
            session.commit()
            await update.message.reply_text(t("feedback_thanks", lang))
        else:
            await update.message.reply_text(t("user_not_found", lang))
        session.close()
        context.user_data["awaiting_feedback"] = False
        return
    currency = context.user_data.get("currency", "RUB")
    passengers = context.user_data.get("filters", {}).get("passengers", 1)
    text = update.message.text.strip().lower()
    parts = text.split()
    if len(parts) not in [2, 3]:
        await update.message.reply_text(t("invalid_format", lang))
        return
    if len(parts) == 2:
        context.user_data['calendar'] = {
            'origin_city': parts[0],
            'dest_city': parts[1],
            'selected': [],
            'month_offset': 0
        }
        await show_calendar(update, context)
        return
    origin_city, dest_city = parts[0], parts[1]
    date_str = parts[2]
    origin_code = get_iata_code(origin_city)
    dest_code = get_iata_code(dest_city)
    if not origin_code or not dest_code:
        await update.message.reply_text(t("city_error", lang))
        return
    depart_date = None
    try:
        parsed_date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
        if parsed_date.date() < datetime.date.today():
            await update.message.reply_text(f"{t('past_date', lang)}: {parsed_date.strftime('%d-%m-%Y')}")
            context.user_data["calendar_mode"] = "search"
            context.user_data["calendar"] = {
                'origin_city': origin_city,
                'dest_city': dest_city,
                'selected': [],
                'month_offset': 0
            }
            await show_calendar(update, context)
            return
        depart_date = parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(t("date_error", lang))
        return
    direct = context.user_data.get("filters", {}).get("direct", False)
    reply_text = get_ticket_price(origin_code, dest_code, origin_city, dest_city, depart_date, currency, lang, passengers, direct=direct)
    if not reply_text and direct:
        alt_reply_text = get_ticket_price(origin_code, dest_code, origin_city, dest_city, depart_date, currency, lang, passengers, direct=False)
        if alt_reply_text:
            if passengers > 1:
                alt_reply_text = f"{alt_reply_text}\n{t('multi_passenger_warning', lang)}"
            await update.message.reply_text(t("no_direct_but_with_transfers", lang))
            await update.message.reply_text(alt_reply_text, parse_mode='Markdown', disable_web_page_preview=True)
            return
    if not reply_text:
        await update.message.reply_text(t("not_found", lang))
        return
    if passengers > 1:
        reply_text += "\n" + t("multi_passenger_warning", lang)
    await update.message.reply_text(reply_text, parse_mode='Markdown', disable_web_page_preview=True)
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    session.close()
    if user:
        save_search_and_results(user, origin_city, dest_city, depart_date, passengers, currency, direct)

async def main():
    init_db()
    fill_airlines()
    fill_currencies()
    fill_translations()
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", choose_language))
    app.add_handler(CommandHandler("filters", filters_command))
    app.add_handler(CallbackQueryHandler(filter_callback, pattern="^passenger_.*|filters_done|filters_reset|toggle_direct$"))
    app.add_handler(CommandHandler("lang", choose_language))
    app.add_handler(CommandHandler("currency", choose_currency))
    app.add_handler(CallbackQueryHandler(currency_callback, pattern="^currency:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset_filters", reset_filters))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("track", track_command))
    app.add_handler(CallbackQueryHandler(track_callback, pattern="^track_.*"))
    app.add_handler(CommandHandler("mytracks", my_tracks))
    app.add_handler(CallbackQueryHandler(untrack_callback, pattern=r"^untrack_\d+$"))
    app.add_handler(CommandHandler("alltracks", all_tracks))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang:"))
    app.add_handler(CommandHandler("history", history_command))
    await app.bot.set_my_commands([
        BotCommand("start", "🔄 Начать заново / Restart"),
        BotCommand("lang", "🌐 Выбрать язык / Choose language"),
        BotCommand("currency", "💱 Установить валюту / Set currency"),
        BotCommand("filters", "🎛 Настроить фильтры / Set filters"),
        BotCommand("reset_filters", "❌ Сбросить фильтры / Reset filters"),
        BotCommand("history", "🕓 История поиска / Search history"),
        BotCommand("track", "📍 Отслеживать маршрут / Track route"),
        BotCommand("mytracks", "📋 Активные отслеживания / Active tracks"),
        BotCommand("alltracks", "🌍 Все отслеживания / All tracks"),
        BotCommand("feedback", "✉️ Оставить отзыв / Leave feedback"),
        BotCommand("help", "ℹ️ Помощь / Help"),
    ])
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    async def run_tracked_check():
        await check_prices_for_all(app.bot)
    scheduler.add_job(run_tracked_check, "interval", minutes=30)
    scheduler.start()
    print("Бот запущен!")
    app.add_handler(CallbackQueryHandler(calendar_callback))
    await app.run_polling()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
