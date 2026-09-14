import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
import jdatetime

SOURCES = [
    {
        "title": "قیمت میلگرد",
        "url": "https://ahanonline.com/product-category/%D9%85%DB%8C%D9%84%DA%AF%D8%B1%D8%AF/%D9%82%DB%8C%D9%85%D8%AA-%D9%85%DB%8C%D9%84%DA%AF%D8%B1%D8%AF/"
    },
    {
        "title": "قیمت ورق سیاه",
        "url": "https://ahanonline.com/product-category/%D8%A7%D9%86%D9%88%D8%A7%D8%B9-%D9%88%D8%B1%D9%82/%D9%88%D8%B1%D9%82-%D8%B3%DB%8C%D8%A7%D9%87/"
    },
    {
        "title": "قیمت تیرآهن",
        "url": "https://ahanonline.com/product-category/%D8%AA%DB%8C%D8%B1%D8%A2%D9%87%D9%86-%D9%88-%D9%87%D8%A7%D8%B4/%D8%AA%DB%8C%D8%B1%D8%A2%D9%87%D9%86/"
    },
    {
        "title": "قیمت لوله پلی اتیلن",
        "url": "https://loolehonline.com/product/2/%D9%84%D9%88%D9%84%D9%87-%D9%BE%D9%84%DB%8C-%D8%A7%D8%AA%DB%8C%D9%84%D9%86"
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7"
}

def fetch_tables_from_url(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=25)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        tables_html = []
        
        for table in soup.find_all("table"):
            for tag in table.find_all(["script", "style", "svg"]):
                tag.decompose()
            
            try:
                dfs = pd.read_html(str(table))
                if dfs and not dfs[0].empty:
                    df = dfs[0].dropna(how='all').fillna('-')
                    clean_html = df.to_html(classes="custom-table", index=False, border=0)
                    tables_html.append(clean_html)
            except Exception:
                tables_html.append(str(table))
                
        return tables_html
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def generate_html_page(data_list):
    now_shamsi = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    sections_html = ""
    for item in data_list:
        sections_html += f"""
        <section class="card">
            <div class="card-header">
                <h2>{item['title']}</h2>
                <a href="{item['url']}" target="_blank" class="source-link">مشاهده صفحه اصلی ↗</a>
            </div>
            <div class="card-body">
        """
        
        if item["tables"]:
            for tbl in item["tables"]:
                sections_html += f'<div class="table-wrapper">{tbl}</div>'
        else:
            sections_html += '<p class="no-data">اطلاعات جدول در دسترس نیست.</p>'
            
        sections_html += """
            </div>
        </section>
        """

    html_template = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>استعلام لحظه‌ای قیمت آهن‌آلات و لوله</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        :root {{
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --primary: #2563eb;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --table-header: #f8fafc;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Vazirmatn', sans-serif;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 24px 16px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: var(--card-bg);
            padding: 20px 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}
        h1 {{
            font-size: 1.3rem;
            font-weight: 800;
        }}
        .update-time {{
            font-size: 0.85rem;
            background: #e0f2fe;
            color: #0369a1;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 24px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }}
        .card-header {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #fafafa;
        }}
        .card-header h2 {{
            font-size: 1.1rem;
            color: #1e293b;
        }}
        .source-link {{
            font-size: 0.85rem;
            color: var(--primary);
            text-decoration: none;
        }}
        .card-body {{
            padding: 16px 20px;
        }}
        .table-wrapper {{
            overflow-x: auto;
            margin-bottom: 16px;
        }}
        .table-wrapper:last-child {{
            margin-bottom: 0;
        }}
        table, .custom-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            text-align: right;
        }}
        th, td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
            white-space: nowrap;
        }}
        th {{
            background-color: var(--table-header);
            color: #334155;
            font-weight: 700;
        }}
        tr:hover {{
            background-color: #f8fafc;
        }}
        .no-data {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 آخرین قیمت‌های استخراج شده</h1>
            <div class="update-time">به‌روزرسانی: {now_shamsi}</div>
        </header>
        <main>
            {sections_html}
        </main>
    </div>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

def main():
    os.makedirs("data", exist_ok=True)
    all_results = []
    
    for source in SOURCES:
        tables = fetch_tables_from_url(source['url'])
        all_results.append({
            "title": source["title"],
            "url": source["url"],
            "tables": tables
        })

    generate_html_page(all_results)
    
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
