import os
import re
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
import jdatetime
from urllib.parse import urlparse

SOURCES_FILE = "sources.json"

def get_domain_fallback(url):
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except Exception:
        return "منبع وب"

def load_sources():
    if not os.path.exists(SOURCES_FILE):
        print(f"Error: {SOURCES_FILE} not found!")
        return []
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            sources = json.load(f)
            # اعتبارسنجی و مقداردهی پیش‌فرض در صورت خالی بودن
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
                    "type": s.get("type", "manual")
                })
            return cleaned
    except Exception as e:
        print(f"Error loading {SOURCES_FILE}: {e}")
        return []

# بقیه بخش‌های scraper.py (شامل fetch_tables_from_url و generate_html_page) بدون تغییر باقی می‌مانند.
