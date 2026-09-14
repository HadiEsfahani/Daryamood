# -*- coding: utf-8 -*-
"""
اسکریپت روزانه خواندن قیمت‌ها از چند سایت و ذخیره در prices.json
این اسکریپت هر روز توسط GitHub Actions اجرا می‌شود.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup, NavigableString

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa,en;q=0.8",
}

TIMEOUT = 25
DEBUG_DIR = "debug_html"

# ---------------------------------------------------------------------------
# لیست سایت‌های مبدأ.
# ---------------------------------------------------------------------------
SOURCES = [
    {
        "type": "generic",
        "name": "میلگرد - آهن آنلاین",
        "url": "https://ahanonline.com/product-category/%D9%85%DB%8C%D9%84%DA%AF%D8%B1%D8%AF/%D9%82%DB%8C%D9%85%D8%AA-%D9%85%DB%8C%D9%84%DA%AF%D8%B1%D8%AF/",
    },
    {
        "type": "generic",
        "name": "ورق سیاه - آهن آنلاین",
        "url": "https://ahanonline.com/product-category/%D8%A7%D9%86%D9%88%D8%A7%D8%B9-%D9%88%D8%B1%D9%82/%D9%88%D8%B1%D9%82-%D8%B3%DB%8C%D8%A7%D9%87/",
    },
    {
        "type": "generic",
        "name": "تیرآهن - آهن آنلاین",
        "url": "https://ahanonline.com/product-category/%D8%AA%DB%8C%D8%B1%D8%A2%D9%87%D9%86-%D9%88-%D9%87%D8%A7%D8%B4/%D8%AA%DB%8C%D8%B1%D8%A2%D9%87%D9%86/",
    },
    {
        "type": "generic",
        "name": "لوله پلی اتیلن - لوله آنلاین",
        "url": "https://loolehonline.com/product/2/%D9%84%D9%88%D9%84%D9%87-%D9%BE%D9%84%DB%8C-%D8%A7%D8%AA%DB%8C%D9%84%D9%86",
    },
]


def fetch(url, source_name):
    """
    گرفتن HTML صفحه. همیشه یک نسخه‌ی خام از پاسخ را در پوشه‌ی debug_html/
    ذخیره می‌کند تا در صورت بروز مشکل، بشود دید سرور واقعاً چه چیزی
    برگردانده (مثلاً صفحه‌ی قیمت‌ها یا یک صفحه‌ی مسدودسازی/کپچا).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
        status = resp.status_code
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] خطا در دریافت {url}: {exc}")
        return None

    os.makedirs(DEBUG_DIR, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9آ-ی]+", "_", source_name)[:60]
    debug_path = os.path.join(DEBUG_DIR, f"{safe_name}.html")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(
        f"[DEBUG] {source_name} -> status={status}, "
        f"طول HTML={len(html)} کاراکتر, ذخیره شد در {debug_path}"
    )

    if status >= 400:
        print(f"[WARN] {source_name}: سرور کد خطای {status} برگرداند.")
        return None

    if len(html) < 2000:
        print(
            f"[WARN] {source_name}: HTML خیلی کوتاه است (احتمال مسدود شدن "
            f"ربات یا نیاز به اجرای جاوااسکریپت). فایل debug را چک کنید."
        )

    return html


# ---------------------------------------------------------------------------
# روش ۱: اگر صفحه واقعاً از تگ <table> استفاده می‌کند و یک ستون هست که
# سرستونش شامل کلمه‌ی "نام" و یکی دیگر شامل "قیمت" است.
# ---------------------------------------------------------------------------
def _parse_by_table(soup):
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
            continue

        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(name_idx, price_idx):
                continue
            name = cells[name_idx].get_text(" ", strip=True)
            price = cells[price_idx].get_text(" ", strip=True)
            if name and price:
                items.append({"name": name, "price": price})

    return items


# ---------------------------------------------------------------------------
# روش ۲: الگوی متنیِ خاص آهن‌آنلاین ("فروش ویژه" قبل از هر ردیف).
# ---------------------------------------------------------------------------
_ROW_SPLIT_RE = re.compile(r"\n\s*فروش ویژه\s*\n")
_PRICE_TOMAN_RIAL_RE = re.compile(r"\+?\s*([\d,]{3,})\s*(ریال|تومان)")


def _parse_by_text_marker(soup):
    text = soup.get_text("\n")
    blocks = _ROW_SPLIT_RE.split(text)[1:]

    items = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        name = lines[0]
        if len(name) < 3 or len(name) > 120:
            continue

        price_match = _PRICE_TOMAN_RIAL_RE.search(block)
        if price_match:
            price = f"{price_match.group(1)} {price_match.group(2)}"
        elif "تماس بگیرید" in block:
            price = "تماس بگیرید"
        else:
            continue

        items.append({"name": name, "price": price})

    return items


# ---------------------------------------------------------------------------
# روش ۳ (عمومی): برای هر متنی در صفحه که به شکل «عدد + ریال/تومان» است،
# نزدیک‌ترین اجدادِ DOM را بالا می‌رویم تا به یک بخش برسیم که هم قیمت را
# دارد هم یک متنِ معنادارِ دیگر (که همان اسم محصول فرض می‌شود). این روش به
# ساختار خاص یک سایت وابسته نیست و برای جدول، div، کارت و... کار می‌کند —
# به شرط اینکه محتوا مستقیماً در HTML باشد (نه با جاوااسکریپت تزریق‌شده).
# ---------------------------------------------------------------------------
_GENERIC_PRICE_RE = re.compile(r"[\d۰-۹][\d۰-۹,٬]{2,}\s*(ریال|تومان)")
_PERSIAN_LETTERS_RE = re.compile(r"[آ-ی]")


def _clean(text):
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_name(text):
    text = _clean(text)
    if not (3 <= len(text) <= 100):
        return False
    if not _PERSIAN_LETTERS_RE.search(text):
        return False
    if _GENERIC_PRICE_RE.search(text):
        return False
    return True


def _find_name_near(price_node):
    """
    از گره‌ی قیمت شروع می‌کند و در والدین پی‌درپی دنبال نزدیک‌ترین متنِ
    معنادار (که خودِ قیمت نیست) می‌گردد — این معمولاً اسم محصول است.
    """
    node = price_node
    for _ in range(6):  # حداکثر ۶ سطح بالا برویم تا کل صفحه را درنوردیم
        node = node.parent
        if node is None:
            break

        candidates = [
            str(child) for child in node.find_all(string=True)
            if isinstance(child, NavigableString)
        ]

        for candidate in candidates:
            if _looks_like_name(candidate):
                return _clean(candidate)

    return None


def _parse_generic(soup):
    items = []
    seen = set()

    price_nodes = soup.find_all(string=_GENERIC_PRICE_RE)
    for price_str in price_nodes:
        price_match = _GENERIC_PRICE_RE.search(str(price_str))
        if not price_match:
            continue
        price = _clean(price_match.group(0))

        name = _find_name_near(price_str)
        if not name:
            continue

        key = (name, price)
        if key in seen:
            continue
        seen.add(key)

        items.append({"name": name, "price": price})

    return items


def parse_source(url, source_name):
    html = fetch(url, source_name)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    for method_name, method in [
        ("marker-text", _parse_by_text_marker),
        ("table", _parse_by_table),
        ("generic", _parse_generic),
    ]:
        raw_items = method(soup)
        if raw_items:
            print(f"[INFO] {source_name}: با روش «{method_name}» {len(raw_items)} ردیف پیدا شد")
            return [{"source": source_name, **item} for item in raw_items]

    print(
        f"[WARN] {source_name}: هیچ روشی جواب نداد. فایل debug_html را چک کنید "
        f"تا ببینید سرور واقعاً چه HTML ای برگردانده است."
    )
    return []


def main():
    all_items = []

    for src in SOURCES:
        items = parse_source(src["url"], src["name"])
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
