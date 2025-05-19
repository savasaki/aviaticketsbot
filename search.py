import logging
import requests
import datetime
from db import SessionLocal
from models import Airline, SearchHistory, SearchResult, User
from utils import t, get_currency_flag, TP_API_TOKEN

def get_iata_code(city_name: str):
    url = 'https://autocomplete.travelpayouts.com/places2'
    params = {'term': city_name, 'locale': 'ru', 'types[]': 'city'}
    response = requests.get(url, params=params)
    data = response.json()
    if data:
        return data[0]['code']
    return None

def get_ticket_price(origin, destination, origin_name, dest_name, requested_date=None, currency="rub", lang="ru", passengers=1, direct=False):
    url = 'https://api.travelpayouts.com/aviasales/v3/prices_for_dates'
    departure_at = requested_date or datetime.date.today().strftime('%Y-%m')
    params = {
        'origin': origin,
        'destination': destination,
        'departure_at': departure_at,
        'one_way': 'true',
        'direct': str(direct).lower(),
        'currency': currency.lower(),
        'sorting': 'price',
        'limit': 30,
        'page': 1,
        'token': TP_API_TOKEN
    }
    response = requests.get(url, params=params)
    data = response.json()
    if not data.get("success") or not data.get("data") or len(data["data"]) == 0:
        return None
    results = data["data"]
    results.sort(key=lambda x: x["departure_at"])
    flag = get_currency_flag(currency)
    route_display = f"{origin_name.title()} → {dest_name.title()}"
    reply_text = f"🎯 {t('route_header', lang)} *{route_display}*\n\n"
    for item in results[:5]:
        price = item.get("price", 0)
        airline_code = item.get("airline", "неизв.")
        session = SessionLocal()
        airline_entry = session.query(Airline).filter_by(code=airline_code).first()
        airline = airline_entry.name_ru if lang == "ru" and airline_entry else airline_code
        session.close()
        departure_raw = item["departure_at"][:10]
        departure_time = datetime.datetime.strptime(departure_raw, "%Y-%m-%d").strftime("%d-%m-%Y")
        total_price = price * passengers
        date_short = datetime.datetime.strptime(departure_raw, "%Y-%m-%d").strftime("%d%m")
        aviasales_link = f"https://www.aviasales.ru/search/{origin}{date_short}{destination}{passengers}"
        reply_text += (
            f"📅 *{departure_time}* — *{total_price} {currency} {flag}* (`{airline}`)\n"
            f"[🔗 {t('buy_button', lang)}]({aviasales_link})\n"
        )
    return reply_text

def save_results_to_db(session, search_id, results, origin_code, dest_code, passengers, currency):
    for item in results:
        try:
            departure_raw = item.get("departure_at", "")[:10]
            departure_date_obj = datetime.datetime.strptime(departure_raw, "%Y-%m-%d").date()
            price = item.get("price", 0)
            airline_code = item.get("airline", "N/A")
            date_short = departure_date_obj.strftime("%d%m")
            link = f"https://www.aviasales.ru/search/{origin_code}{date_short}{dest_code}{passengers}"
            session.add(SearchResult(
                search_id=search_id,
                airline_code=airline_code,
                departure_date=departure_date_obj,
                price=price,
                currency=currency.upper(),
                link=link
            ))
        except Exception as e:
            logging.warning(f"❗ Ошибка при сохранении SearchResult: {e}")

def save_search_and_results(user, origin_city, dest_city, depart_date, passengers, currency, direct, raw_data=None):
    session = SessionLocal()
    search = SearchHistory(
        user_id=user.id,
        origin_city=origin_city,
        destination_city=dest_city,
        depart_date=depart_date,
        passengers=passengers,
        direct_only=direct
    )
    session.add(search)
    session.commit()
    if raw_data is None:
        origin_code = get_iata_code(origin_city)
        dest_code = get_iata_code(dest_city)
        raw_data = fetch_ticket_data(origin_code, dest_code, depart_date, currency, passengers, direct)
    else:
        origin_code = get_iata_code(origin_city)
        dest_code = get_iata_code(dest_city)
    if not isinstance(raw_data, list):
        logging.warning(f"❌ fetch_ticket_data вернул {type(raw_data)}, ожидается список")
        raw_data = []
    save_results_to_db(
        session=session,
        search_id=search.id,
        results=raw_data,
        origin_code=origin_code,
        dest_code=dest_code,
        passengers=passengers,
        currency=currency
    )
    session.commit()
    session.close()

def fetch_ticket_data(origin_code, dest_code, depart_date, currency, passengers=1, direct=False):
    if isinstance(depart_date, datetime.datetime):
        depart_date = depart_date.date().isoformat()
    elif isinstance(depart_date, datetime.date):
        depart_date = depart_date.isoformat()
    elif not isinstance(depart_date, str):
        logging.warning("❌ Неправильный тип даты")
        return []
    params = {
        'origin': origin_code,
        'destination': dest_code,
        'departure_at': depart_date,
        'currency': currency.lower(),
        'limit': 5,
        'token': TP_API_TOKEN
    }
    if direct:
        params['direct'] = 'true'
    try:
        response = requests.get('https://api.travelpayouts.com/aviasales/v3/prices_for_dates', params=params)
        if response.status_code != 200:
            logging.warning(f"API вернул {response.status_code}: {response.text}")
            return []
        data = response.json()
        raw_data = data.get("data", [])
        if isinstance(raw_data, dict):
            return list(raw_data.values())
        elif isinstance(raw_data, list):
            return raw_data
        else:
            return []
    except Exception as e:
        logging.warning(f"Ошибка запроса: {e}")
        return []

async def process_selected_dates(update, context):
    data = context.user_data.get('calendar')
    origin_city, dest_city = data['origin_city'], data['dest_city']
    currency = context.user_data.get("currency", "RUB")
    lang = context.user_data.get("lang", "ru")
    if not data['selected']:
        await update.effective_message.reply_text(t("calendar_no_dates", lang))
        return
    origin_code = get_iata_code(origin_city)
    dest_code = get_iata_code(dest_city)
    if not origin_code or not dest_code:
        await update.effective_message.reply_text(t("city_error", lang))
        return
    passengers = context.user_data.get("filters", {}).get("passengers", 1)
    sorted_dates = sorted(data['selected'], key=lambda d: datetime.datetime.strptime(d, "%d-%m-%Y"))
    found_any = False
    all_replies = ""
    for d in sorted_dates:
        try:
            parsed = datetime.datetime.strptime(d, "%d-%m-%Y")
            if parsed.date() < datetime.date.today():
                all_replies += f"{t('past_date', lang)} ({parsed.strftime('%d-%m-%Y')})\n\n"
                continue
            formatted = parsed.strftime("%Y-%m-%d")
            direct = context.user_data.get("filters", {}).get("direct", False)
            reply = get_ticket_price(origin_code, dest_code, origin_city, dest_city, formatted, currency, lang, passengers, direct=direct)
            if not reply and direct:
                alt_reply = get_ticket_price(origin_code, dest_code, origin_city, dest_city, formatted, currency, lang, passengers, direct=False)
                if alt_reply:
                    warning_text = t("no_direct_but_with_transfers", lang) + "\n"
                    all_replies += warning_text + alt_reply + "\n\n"
                    found_any = True
                    session = SessionLocal()
                    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
                    session.close()
                    if user:
                        save_search_and_results(user, origin_city, dest_city, formatted, passengers, currency, False)
                    continue
            if reply:
                all_replies += reply + "\n"
                found_any = True
                session = SessionLocal()
                telegram_id = update.effective_user.id
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                if user:
                    search = SearchHistory(
                        user_id=user.id,
                        origin_city=origin_city,
                        destination_city=dest_city,
                        depart_date=formatted,
                        passengers=passengers,
                        direct_only=direct
                    )
                    session.add(search)
                    session.commit()
                    results_raw = fetch_ticket_data(
                        origin_code,
                        dest_code,
                        formatted,
                        currency,
                        passengers,
                        direct
                    )
                    if not isinstance(results_raw, list):
                        logging.warning(f"❌ fetch_ticket_data вернул {type(results_raw)}, ожидается список")
                        results_raw = []
                    save_results_to_db(
                        session=session,
                        search_id=search.id,
                        results=results_raw,
                        origin_code=origin_code,
                        dest_code=dest_code,
                        passengers=passengers,
                        currency=currency
                    )
                    session.commit()
                session.close()
        except Exception as e:
            logging.warning(f"Ошибка при обработке даты {d}: {e}")
            continue
    if passengers > 1 and found_any:
        all_replies += "\n" + t("multi_passenger_warning", lang)
    if all_replies:
        await update.effective_message.reply_text(all_replies.strip(), parse_mode='Markdown', disable_web_page_preview=True)
    else:
        await update.effective_message.reply_text(t("not_found", lang))
