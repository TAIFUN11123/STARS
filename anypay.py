"""
Anypay для бота @taifstars_bot (aiogram). Кладётся рядом с основным файлом бота.
Ничего не знает про сам бот: только строит ссылку на оплату и спрашивает статус платежа.

Переменные окружения (задаются в BotHost, в код НЕ вставляются):
    ANYPAY_MERCHANT_ID  - ID проекта из кабинета Anypay
    ANYPAY_SECRET       - секретный ключ проекта
    ANYPAY_API_ID       - API ID
    ANYPAY_API_KEY      - API-ключ
    ANYPAY_DEBUG=1      - (по желанию) печатать в лог сырые ответы Anypay

ДВА МЕСТА, КОТОРЫЕ НАДО СВЕРИТЬ С ДОКУМЕНТАЦИЕЙ ANYPAY (помечены ПРОВЕРИТЬ ПО ДОКЕ):
    1) make_form_sign() и адрес формы в payment_link()
    2) fetch_paid_amount()
Если формулы окажутся другими, бот просто не увидит оплату (товар не выдастся),
а не выдаст товар бесплатно: так устроено специально.
"""
import hashlib
import os
from urllib.parse import urlencode

import aiohttp

MERCHANT_ID = os.getenv("ANYPAY_MERCHANT_ID")
SECRET = os.getenv("ANYPAY_SECRET")
API_ID = os.getenv("ANYPAY_API_ID")
API_KEY = os.getenv("ANYPAY_API_KEY")
DEBUG = os.getenv("ANYPAY_DEBUG", "0") == "1"

ANYPAY_ENABLED = bool(MERCHANT_ID and SECRET and API_ID and API_KEY)

BOT_URL = "https://t.me/taifstars_bot"


def make_form_sign(pay_id, amount, currency, desc, success_url, fail_url) -> str:
    # ПРОВЕРИТЬ ПО ДОКЕ: порядок полей и алгоритм (в кабинете выбран SHA256)
    raw = ":".join([
        str(MERCHANT_ID), str(pay_id), f"{amount:.2f}", currency, desc,
        success_url, fail_url, SECRET,
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


def payment_link(pay_id: int, amount: float, desc: str) -> str:
    currency = "RUB"
    params = {
        "merchant_id": MERCHANT_ID,
        "pay_id": pay_id,
        "amount": f"{amount:.2f}",
        "currency": currency,
        "desc": desc,
        "success_url": BOT_URL,
        "fail_url": BOT_URL,
        "sign": make_form_sign(pay_id, amount, currency, desc, BOT_URL, BOT_URL),
    }
    # ПРОВЕРИТЬ ПО ДОКЕ: адрес платёжной формы
    return "https://anypay.io/merchant?" + urlencode(params)


async def fetch_paid_amount(pay_id: int):
    """Возвращает сумму, если заказ оплачен, иначе None."""
    # ПРОВЕРИТЬ ПО ДОКЕ: URL метода, имена полей, формула подписи, значение статуса "оплачен",
    # и что именно лежит в amount (сумма платежа или сумма за вычетом комиссии).
    method = "payments"
    sign = hashlib.sha256(f"{method}{API_ID}{MERCHANT_ID}{API_KEY}".encode()).hexdigest()
    url = f"https://anypay.io/api/{method}/{API_ID}"
    form = {"project_id": MERCHANT_ID, "pay_id": str(pay_id), "sign": sign}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=15)) as r:
            data = await r.json(content_type=None)

    if DEBUG:
        print(f"[anypay] pay_id={pay_id} ответ: {data}")

    payments = (data.get("result") or {}).get("payments") or {}
    items = payments.values() if isinstance(payments, dict) else payments
    for p in items:
        if str(p.get("pay_id")) == str(pay_id) and p.get("status") == "paid":
            return float(p.get("amount", 0))
    return None
