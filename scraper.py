# -*- coding: utf-8 -*-
"""
اسکریپت روزانه خواندن قیمت‌ها از چند سایت و ذخیره در prices.json
این اسکریپت هر روز توسط GitHub Actions اجرا می‌شود.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.8",
}

TIMEOUT = 25

# ---------------------------------------------------------------------------
# لیست سایت‌های مبدأ. هر سایت با "type" مشخص می‌شود که تعیین می‌کند
# کدام تابع برای استخراج قیمت از آن استفاده شود.
# ---------------------------------------------------------------------------
SOURCES = [
    {
        "type": "ahanonline_category",
        "name": "میلگرد - آهن آنلاین",
        "url": "https://ahanonline.com/product-category/%D9%85%DB%8C%D9%84%DA%AF%D8%B1%D8%AF/%D9%82%DB%8C%D9%85%D8%AA-%D9%85%DB%8C%D9%84%DA%AF%D8%B1%D8%AF/",
    },
    {
        "type": "ahanonline_category",
        "name": "ورق سیاه - آهن آنلاین",
        "url": "https://ahanonline.com/product-category/%D8%A7%D9%86%D9%88%D8%A7%D8%B9-%D9%88%D8%B1%D9%82/%D9%88%D8%B1%D9%82-%D8%B3%DB%8C%D8%A7%D9%87/",
    },
    {
        "type": "ahanonline_category",
        "name": "تیرآهن - آهن آنلاین",
        "url": "https://ahanonline.com/product-category/%D8%AA%DB%8C%D8%B1%D8%A2%D9%87%D9%86-%D9%88-%D9%87%D8%A7%D8%B4/%D8%AA%DB%8C%D8%B1%D8%A2%D9%87%D9%86/",
    },
    {
        "type": "looleh_product",
        "name": "لوله پلی اتیلن - لوله آنلاین",
        "url": "https://loolehonline.com/product/2/%D9%84%D9%88%D9%84%D9%87-%D9%BE%D9%84%DB%8C-%D8%A7%D8%AA%DB%8C%D9%84%D9%86",
    },
]


def fetch(url):
    """گرفتن HTML صفحه. در صورت خطا None برمی‌گرداند و اجرای اسکریپت متوقف نمی‌شود."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] خطا در دریافت {url}: {exc}")
        return None


def _parse_ahanonline_by_table(soup):
    """
    تلاش اول: اگر سایت واقعاً از تگ <table> استفاده کند، از روی سرستون‌ها
    ("نام"، "قیمت") ستون‌های موردنیاز پیدا می‌شوند.
    """
    items = []
    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue

        header_cells = header_row.find_all(["th", "td"])
        headers_text = [c.get_text(strip=True) for c in header_cells]

        name_idx = next((i for i, h in enumerate(headers_text) if "نام" in h), None)
        price_idx = next((i for i, h in enumerate(headers_text) if "قیمت" in h), None)

        if name_idx is None or price_idx is None:
            continue  # این جدول، جدول قیمت نیست (مثلاً جدول اخبار)

        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(name_idx, price_idx):
                continue

            name = cells[name_idx].get_text(" ", strip=True)
            price = cells[price_idx].get_text(" ", strip=True)

            if not name or not price:
                continue

            items.append({"name": name, "price": price})

    return items


# هر ردیف قیمت در آهن‌آنلاین همیشه با برچسب "فروش ویژه" مشخص شده و بلافاصله
# بعدش نام کامل محصول می‌آید. این روش کاری به این ندارد که HTML زیرین
# <table> است یا <div> — فقط به متنِ قابل‌مشاهده‌ی صفحه نگاه می‌کند، پس در
# برابر تغییر قالب (جدول یا نه) مقاوم‌تر است.
_ROW_SPLIT_RE = re.compile(r"\n\s*فروش ویژه\s*\n")
_PRICE_RE = re.compile(r"\+\s*([\d,]+)\s*ریال")


def _parse_ahanonline_by_text(soup):
    text = soup.get_text("\n")
    blocks = _ROW_SPLIT_RE.split(text)[1:]  # بلاک اول قبل از اولین "فروش ویژه" است

    items = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        name = lines[0]

        price_match = _PRICE_RE.search(block)
        if price_match:
            price = f"+ {price_match.group(1)} ریال"
        elif "تماس بگیرید" in block:
            price = "تماس بگیرید"
        else:
            continue

        # فیلتر خطوط بی‌ربط (خیلی کوتاه یا خیلی بلند) که احتمالاً اسم محصول نیستند
        if len(name) < 3 or len(name) > 120:
            continue

        items.append({"name": name, "price": price})

    return items


def parse_ahanonline_category(url, source_name):
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    raw_items = _parse_ahanonline_by_text(soup)
    method = "text"

    if not raw_items:
        raw_items = _parse_ahanonline_by_table(soup)
        method = "table"

    if not raw_items:
        print(f"[WARN] هیچ ردیفی برای {source_name} پیدا نشد؛ ساختار صفحه احتمالاً عوض شده.")
        return []

    print(f"[INFO] {source_name}: با روش «{method}» استخراج شد")
    return [{"source": source_name, **item} for item in raw_items]


def parse_looleh_product(url, source_name):
    """
    صفحه‌ی یک محصول تکی. چند حالتِ رایج نمایش قیمت در قالب‌های ووکامرس/فروشگاهی
    امتحان می‌شود و در صورت شکست، با regex دنبال عددی که قبل/بعدش کلمه‌ی
    «تومان» یا «ریال» آمده می‌گردیم.
    """
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    name = title_tag.get_text(strip=True) if title_tag else source_name

    price_text = None
    for selector in [
        ".price",
        ".woocommerce-Price-amount",
        "[itemprop='price']",
        ".product-price",
        ".price-value",
    ]:
        tag = soup.select_one(selector)
        if tag:
            candidate = tag.get_text(" ", strip=True)
            if candidate:
                price_text = candidate
                break

    if not price_text:
        match = re.search(r"[\d,٬۰-۹]{4,}\s*(تومان|ریال)", html)
        if match:
            price_text = match.group(0).strip()

    if not price_text:
        print(f"[WARN] قیمت برای {url} پیدا نشد؛ ممکن است ساختار صفحه عوض شده باشد.")
        return []

    return [{"source": source_name, "name": name, "price": price_text}]


PARSERS = {
    "ahanonline_category": parse_ahanonline_category,
    "looleh_product": parse_looleh_product,
}


def main():
    all_items = []

    for src in SOURCES:
        parser = PARSERS.get(src["type"])
        if not parser:
            continue
        items = parser(src["url"], src["name"])
        print(f"[INFO] {src['name']}: {len(items)} ردیف پیدا شد")
        all_items.extend(items)

    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now_str = datetime.now(tehran_tz).strftime("%Y-%m-%d %H:%M")

    output = {
        "updated_at": now_str,
        "items": all_items,
    }

    with open("prices.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[DONE] مجموعاً {len(all_items)} ردیف در prices.json ذخیره شد.")


if __name__ == "__main__":
    main()
