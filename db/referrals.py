import logging
import aiohttp
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from typing import Optional
from aiogram.fsm.state import StatesGroup, State
from .base import get_db_connection

logger = logging.getLogger(__name__)


# =========================
# FSM
# =========================
class AdminUpdateLinkFSM(StatesGroup):
    select_bank = State()
    select_product = State()
    select_variant = State()
    enter_base_url = State()
    confirm = State()

# =========================
# SHORTENER
# =========================
async def shorten_link(url: str) -> str:
    api = "https://clck.ru/--"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api, data={"url": url}) as resp:
                if resp.status != 200:
                    logger.warning(f"❌ Ошибка при сокращении ссылки: HTTP {resp.status}")
                    return url
                short_url = await resp.text()
                return short_url.strip()
    except Exception as e:
        logger.warning(f"❌ Ошибка при сокращении ссылки: {e}")
        return url

# =========================
# GET REFERRAL LINK
# =========================
async def get_referral_link(
    bank_key: str,
    product_key: str,
    variant_key: str | None = None,
    shorten: bool = False
) -> Optional[str]:

    async with get_db_connection() as db:
        row = None

        if variant_key:
            cur = await db.execute(
                """
                SELECT base_url, utm_source, utm_medium, utm_campaign
                FROM referral_links
                WHERE bank_key = ?
                  AND product_key = ?
                  AND variant_key = ?
                  AND is_active = 1
                LIMIT 1
                """,
                (bank_key, product_key, variant_key)
            )
            row = await cur.fetchone()

        if row is None:
            cur = await db.execute(
                """
                SELECT base_url, utm_source, utm_medium, utm_campaign
                FROM referral_links
                WHERE bank_key = ?
                  AND product_key = ?
                  AND variant_key IS NULL
                  AND is_active = 1
                LIMIT 1
                """,
                (bank_key, product_key)
            )
            row = await cur.fetchone()

        if row is None:
            return None

        base_url = row["base_url"]

        utm_params = {
            "utm_source": row["utm_source"] or "ReferralFlowBot",
            "utm_medium": row["utm_medium"] or "organic",
            "utm_campaign": row["utm_campaign"] or (variant_key or product_key),
        }

        parsed = urlparse(base_url)
        existing_params = parse_qs(parsed.query)

        flat_existing = {k: v[0] for k, v in existing_params.items() if v}

        merged_params = {**flat_existing, **{k: v for k, v in utm_params.items() if v is not None},}

        final_url = urlunparse(parsed._replace(query=urlencode(merged_params)))

        if shorten:
            final_url = await shorten_link(final_url)

        return final_url


# =========================
# UPDATE REFERRAL LINK
# =========================
async def update_referral_link(
    bank_key: str,
    product_key: str,
    base_url: str,
    variant_key: str | None = None,
    utm_source: str = "ReferralFlowBot",
    utm_medium: str = "referral",
    utm_campaign: str = "default",
) -> bool:
    bank_key = bank_key.lower()
    product_key = product_key.lower()

    async with get_db_connection() as db:
        try:
            await db.execute("""
                INSERT INTO referral_links
                (bank_key, product_key, variant_key, base_url, utm_source, utm_medium, utm_campaign, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(bank_key, product_key, variant_key) DO UPDATE SET
                    base_url = excluded.base_url,
                    utm_source = excluded.utm_source,
                    utm_medium = excluded.utm_medium,
                    utm_campaign = excluded.utm_campaign,
                    updated_at = CURRENT_TIMESTAMP
            """, (bank_key, product_key, variant_key, base_url, utm_source, utm_medium, utm_campaign))

            await db.commit()
            return True
        except Exception as e:
            logger.error(f"❌ update_referral_link error: {e}")
            return False