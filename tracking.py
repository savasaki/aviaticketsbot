import logging
import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from db import SessionLocal
from models import User, TrackedRoute, Notification
from utils import t, build_tracking_settings_keyboard
from search import get_iata_code, fetch_ticket_data

async def track_command(update, context):
    lang = context.user_data.get("lang", "ru")
    context.user_data["track_mode"] = True
    await update.message.reply_text(
        t("track_start_prompt", lang),
        parse_mode='Markdown'
    )

async def track_callback(update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    if query.data in ("track_price", "track_percent"):
        await query.edit_message_reply_markup(reply_markup=None)
        context.user_data["track_awaiting"] = "price" if query.data == "track_price" else "percent"
        msg_key = "track_enter_price" if query.data == "track_price" else "track_enter_percent"
        await query.message.reply_text(t(msg_key, lang))
    elif query.data == "track_cancel":
        context.user_data.pop("track", None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(t("track_cancelled", lang))
    elif query.data == "track_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        track_data = context.user_data.get("track", {})
        if not track_data.get("price") and not track_data.get("percent"):
            await query.message.reply_text(
                t("track_confirm_missing", lang),
                reply_markup=build_tracking_settings_keyboard(lang, track_data.get("price"), track_data.get("percent"))
            )
            return
        await save_tracked_route(update, context)

async def save_tracked_route(update, context):
    session = SessionLocal()
    telegram_id = update.effective_user.id
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    lang = context.user_data.get("lang", "ru")
    if not user:
        await update.effective_message.reply_text(t("user_not_found", lang))
        session.close()
        return
    data = context.user_data.get("track", {})
    origin = data.get("origin")
    dest = data.get("destination")
    price = data.get("price")
    percent = data.get("percent")
    dates = []
    if data.get("date"):
        dates = [data["date"]]
    elif data.get("selected_dates"):
        dates = data["selected_dates"]
    for d in dates:
        route = TrackedRoute(
            user_id=user.id,
            currency=user.currency,
            origin_city=origin,
            destination_city=dest,
            depart_date=d,
            notify_below_price=price,
            price_drop_percent=percent,
            active=True
        )
        session.add(route)
    session.commit()
    session.close()
    msg = t("track_saved", lang, n=len(dates))
    await update.effective_message.reply_text(msg)
    context.user_data.pop("track", None)

async def my_tracks(update, context):
    lang = context.user_data.get("lang", "ru")
    session = SessionLocal()
    telegram_id = update.effective_user.id
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        await update.message.reply_text(t("user_not_found", lang))
        session.close()
        return
    tracks = session.query(TrackedRoute).filter_by(user_id=user.id, active=True).all()
    if not tracks:
        await update.message.reply_text(t("no_active_tracks", lang))
        session.close()
        return
    for route in tracks:
        text = (
            f"📌 *{route.origin_city.title()} → {route.destination_city.title()}*"
            f"\n📅 {route.depart_date}"
        )
        currency = route.currency or user.currency
        if route.notify_below_price:
            price_label = t("track_price_label", lang)
            text += f"\n💰 {price_label} ≤ {route.notify_below_price} {currency}"
        if route.price_drop_percent:
            percent_label = t("track_percent_label", lang)
            text += f"\n📉 {percent_label} -{route.price_drop_percent}%"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t("untrack_button", lang), callback_data=f"untrack_{route.id}")
        ]])
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)
    session.close()

async def all_tracks(update, context):
    lang = context.user_data.get("lang", "ru")
    session = SessionLocal()
    telegram_id = update.effective_user.id
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        await update.message.reply_text(t("user_not_found", lang))
        session.close()
        return
    tracks = session.query(TrackedRoute).filter_by(user_id=user.id).order_by(TrackedRoute.created_at.desc()).limit(5).all()
    if not tracks:
        await update.message.reply_text(t("no_all_tracks", lang))
        session.close()
        return
    for route in tracks:
        status = t("status_active", lang) if route.active else t("status_cancelled", lang)
        text = (
            f"📌 *{route.origin_city.title()} → {route.destination_city.title()}*"
            f"\n📅 {route.depart_date}"
        )
        currency = route.currency or user.currency
        if route.notify_below_price:
            text += f"\n💰 ≤ {route.notify_below_price} {currency}"
        if route.price_drop_percent:
            text += f"\n📉 -{route.price_drop_percent}%"
        text += f"\n{status}"
        await update.message.reply_text(text, parse_mode='Markdown')
    session.close()

async def untrack_callback(update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "ru")
    route_id = int(query.data.split("_")[1])
    session = SessionLocal()
    telegram_id = update.effective_user.id
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    route = session.query(TrackedRoute).filter_by(id=route_id, user_id=user.id, active=True).first()
    if route:
        route.active = False
        session.commit()
        await query.edit_message_text(t("untrack_cancelled", lang))
    else:
        await query.edit_message_text(t("untrack_not_found", lang))
    session.close()

async def send_notification(bot, user, route: TrackedRoute, message_text: str, reply_markup=None):
    session = SessionLocal()
    notification = Notification(
        user_id=user.id,
        route_id=route.id,
        message=message_text
    )
    session.add(notification)
    session.commit()
    session.close()
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        print(t("notification_error", user.language, error=str(e)))

async def check_prices_for_all(bot):
    session = SessionLocal()
    routes = session.query(TrackedRoute).filter_by(active=True).all()
    for route in routes:
        user = session.query(User).filter_by(id=route.user_id).first()
        if not user:
            continue
        if isinstance(route.depart_date, datetime.date):
            depart_str = route.depart_date.isoformat()
        elif isinstance(route.depart_date, str):
            try:
                parsed_date = datetime.datetime.strptime(route.depart_date, "%d-%m-%Y")
                depart_str = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                logging.warning(f"❌ Невозможно преобразовать дату: {route.depart_date}")
                continue
        else:
            logging.warning(f"⚠️ Неподдерживаемый формат даты: {route.depart_date}")
            continue
        results = fetch_ticket_data(
            get_iata_code(route.origin_city),
            get_iata_code(route.destination_city),
            depart_str,
            route.currency,
            passengers=1,
            direct=False
        )
        if not results:
            continue
        current_price = min(item.get("price", 0) for item in results)
        previous_price = route.last_checked_price or current_price
        should_notify = False
        if route.notify_below_price and current_price <= route.notify_below_price:
            should_notify = True
        if route.price_drop_percent:
            drop = (previous_price - current_price) / previous_price * 100
            if drop >= route.price_drop_percent:
                if not route.last_notified_percent or drop > route.last_notified_percent:
                    should_notify = True
                    route.last_notified_percent = int(drop)
        if should_notify:
            if current_price == route.last_notified_price:
                continue
            triggers = []
            if route.notify_below_price is not None:
                triggers.append(t("notification_price_condition", user.language, price=route.notify_below_price))
            if route.price_drop_percent is not None:
                triggers.append(t("notification_percent_condition", user.language, percent=route.price_drop_percent))
            trigger_text = " и ".join(triggers) if user.language == "ru" else ", ".join(triggers)
            trigger_info = f" ({trigger_text})" if triggers else ""
            message = t(
                "notification_text",
                user.language,
                origin=route.origin_city.title(),
                destination=route.destination_city.title(),
                date=route.depart_date,
                price=current_price,
                currency=route.currency,
                condition=trigger_info,
            )
            origin_code = get_iata_code(route.origin_city)
            dest_code = get_iata_code(route.destination_city)
            date_short = datetime.datetime.strptime(route.depart_date, "%d-%m-%Y").strftime("%d%m")
            aviasales_url = f"https://www.aviasales.ru/search/{origin_code}{date_short}{dest_code}1"
            buttons = [
                [InlineKeyboardButton(t("buy_button", user.language), url=aviasales_url)],
                [InlineKeyboardButton(t("stop_tracking", user.language), callback_data=f"untrack_{route.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await send_notification(bot, user, route, message, reply_markup=reply_markup)
            route.last_notified_price = current_price
    session.commit()
    session.close()
