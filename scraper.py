# -*- coding: utf-8 -*-
"""
استخراج جدول‌های قیمت از منابع sources.json و ساخت index.html نهایی.

روش کار: برخلاف سایت‌هایی که قیمت را با div/span نمایش می‌دهند، منابع این
پروژه از تگ واقعی <table> استفاده می‌کنند. برای همین به‌جای نوشتن پارسر
دستی برای هر سایت، از pandas.read_html() استفاده می‌شود که خودش هر
<table> موجود در صفحه را به یک DataFrame تبدیل می‌کند — همان چیزی که در
index.html قبلی هم دیده می‌شود (کلاس‌های dataframe / custom-table).
"""

import io
import json
import os
from datetime import datetime
from urllib.parse import urlparse

import jdatetime
import pandas as pd
import requests

try:
    from zoneinfo import ZoneInfo
    TEHRAN_TZ = ZoneInfo("Asia/Tehran")
except Exception:  # noqa: BLE001 - محیط‌های خیلی قدیمی پایتون
    TEHRAN_TZ = None

SOURCES_FILE = "sources.json"
TEMPLATE_FILE = "template.html"
OUTPUT_FILE = "index.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.8",
}
TIMEOUT = 25


def get_domain_fallback(url):
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except Exception:  # noqa: BLE001
        return "منبع وب"


def load_sources():
    if not os.path.exists(SOURCES_FILE):
        print(f"Error: {SOURCES_FILE} not found!")
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"Error loading {SOURCES_FILE}: {e}")
        return []

    cleaned = []
    for s in sources:
        if not s.get("url"):
            continue
        url = s["url"].strip()
        title = s.get("title", "").strip() or "قیمت مصالح"
        source_name = s.get("source_name", "").strip() or get_domain_fallback(url)
        cleaned.append({
            "title": title,
            "source_name": source_name,
            "url": url,
            "type": s.get("type", "manual"),
        })
    return cleaned


def fetch_tables_from_url(url):
    """
    HTML صفحه را می‌گیرد و تمام جدول‌های واقعی <table> داخل آن را به شکل
    یک لیست از رشته‌های HTML (هر کدام یک <div class="table-wrapper">)
    برمی‌گرداند. در صورت هر نوع خطا (شبکه، عدم وجود جدول و...) لیست خالی
    برمی‌گردد — این باعث توقف اسکریپت نمی‌شود، فقط همان یک منبع خالی
    نمایش داده می‌شود.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
    except Exception as exc:  # noqa: BLE001
        print(f"  [WARN] خطا در دریافت صفحه: {exc}")
        return []

    try:
        dataframes = pd.read_html(io.StringIO(resp.text))
    except ValueError:
        # pandas وقتی هیچ <table> ای در صفحه پیدا نکند همین خطا را می‌دهد
        print("  [WARN] هیچ تگ <table> ای در این صفحه پیدا نشد.")
        return []
    except Exception as exc:  # noqa: BLE001
        print(f"  [WARN] خطا در پردازش جدول‌ها: {exc}")
        return []

    wrapped_tables = []
    seen_html = set()

    for df in dataframes:
        # جدول‌های خیلی کوچک (مثلاً منوهای ناوبری) را رد کن
        if df.shape[0] < 1 or df.shape[1] < 2:
            continue

        # جدول‌هایی که همه‌ی سلول‌هایشان خالی/NaN است را رد کن
        if df.isna().all(axis=None):
            continue

        table_html = df.to_html(
            classes="custom-table",
            index=False,
            border=0,
            na_rep="",
            escape=False,
        )

        # اگر همین جدول عیناً تکرار شده بود (بعضی سایت‌ها یک جدول را دو بار می‌گذارند) رد کن
        if table_html in seen_html:
            continue
        seen_html.add(table_html)

        wrapped_tables.append(f'<div class="table-wrapper">{table_html}</div>')

    return wrapped_tables


def build_card_html(source, tables):
    if tables:
        body = "".join(tables)
    else:
        body = '<p class="no-data">اطلاعات جدول در دسترس نیست.</p>'

    return f"""        <section class="card">
            <div class="card-header">
                <h2>{source['title']}</h2>
                <a href="{source['url']}" target="_blank" class="source-link">مشاهده صفحه اصلی ↗</a>
            </div>
            <div class="card-body">
        {body}
            </div>
        </section>
        """


def current_time_str():
    if TEHRAN_TZ:
        now = datetime.now(TEHRAN_TZ)
    else:
        now = datetime.now()
    jnow = jdatetime.datetime.fromgregorian(datetime=now)
    return jnow.strftime("%Y/%m/%d - %H:%M")


def generate_html_page(sources_with_tables):
    if not os.path.exists(TEMPLATE_FILE):
        raise FileNotFoundError(
            f"{TEMPLATE_FILE} پیدا نشد. این فایل قالب ثابت صفحه (استایل/اسکریپت) "
            f"است و باید کنار scraper.py در ریپو باشد."
        )

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    cards_html = "\n".join(
        build_card_html(source, tables) for source, tables in sources_with_tables
    )

    final_html = (
        template
        .replace("{{CARDS}}", cards_html)
        .replace("{{UPDATED_AT}}", current_time_str())
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)


def main():
    sources = load_sources()
    if not sources:
        print("[ERROR] هیچ منبعی برای بررسی وجود ندارد.")
        return

    sources_with_tables = []
    failed = []

    for idx, source in enumerate(sources, start=1):
        print(f"[{idx}/{len(sources)}] {source['title']} - {source['source_name']}")
        tables = fetch_tables_from_url(source["url"])
        print(f"  → {len(tables)} جدول پیدا شد")
        if not tables:
            failed.append(f"{source['title']} - {source['source_name']}")
        sources_with_tables.append((source, tables))

    generate_html_page(sources_with_tables)

    print(f"\n[DONE] {OUTPUT_FILE} با {len(sources)} منبع بازسازی شد.")
    if failed:
        print(f"\n[SUMMARY] {len(failed)} منبع بدون جدول ماندند:")
        for name in failed:
            print(f"   - {name}")


if __name__ == "__main__":
    main()
