import os, json, requests, io
import pandas as pd
from bs4 import BeautifulSoup
import jdatetime

# --- خواندن منابع از فایل جیسون تولید شده توسط پنل ادمین ---
def load_sources():
    if os.path.exists("sources.json"):
        with open("sources.json", "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("خطا: فایل sources.json نامعتبر است.")
                return []
    print("خطا: فایل sources.json پیدا نشد.")
    return []

SOURCES = load_sources()

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
        
        soup = BeautifulSoup(response.text, 'lxml')
        tables = soup.find_all('table')
        extracted_tables = []
        
        for table in tables:
            # حذف اسکریپت‌ها، استایل‌ها و تصاویر اضافی
            for tag in table(['script', 'style', 'svg', 'img', 'button']):
                tag.decompose()
            
            # --- حذف هایپرلینک‌ها (لینک‌ها) و نگه داشتن فقط متن کالاها ---
            for a in table.find_all('a'):
                a.unwrap()
                
            try:
                # خواندن جدول با کتابخانه پانداز
                df = pd.read_html(io.StringIO(str(table)))[0]
                df = df.dropna(how='all').fillna('-')
                html_table = df.to_html(classes="custom-table", index=False, border=0)
                extracted_tables.append(html_table)
            except Exception:
                # در صورت خطا در پانداز، جدول به عنوان HTML ساده وارد می‌شود (بدون لینک)
                extracted_tables.append(str(table))
                
        return extracted_tables
    except Exception as e:
        print(f"Error fetching {url}: {e}")
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
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --primary: #2563eb;
            --text-main: #1e293b;
            --text-muted: #475569;
            --border-color: #cbd5e1;
            --table-header: #334155;
            --table-header-text: #ffffff;
            --row-hover: #f1f5f9;
            --card-header-bg: #1e293b;
        }}
        
        body {{
            font-family: 'Vazirmatn', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 2;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 1.8rem;
            color: var(--text-main);
            margin-bottom: 10px;
        }}
        
        .update-time {{
            display: inline-block;
            background-color: #e2e8f0;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 20px;
        }}

        .search-box {{
            width: 100%;
            max-width: 500px;
            padding: 14px 20px;
            font-size: 1rem;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 30px;
            font-family: 'Vazirmatn', sans-serif;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.3s;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
        }}
        
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 30px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }}
        
        .card-header {{
            background-color: var(--card-header-bg);
            padding: 15px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .card-header h2 {{
            margin: 0;
            font-size: 1.3rem;
            color: #ffffff;
        }}
        
        .source-link {{
            color: #93c5fd;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: color 0.2s;
        }}
        
        .source-link:hover {{
            color: #bfdbfe;
        }}
        
        .card-body {{
            padding: 25px;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            margin-bottom: 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        
        .table-wrapper:last-child {{
            margin-bottom: 0;
        }}
        
        table, .custom-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: right;
            font-size: 1rem;
            white-space: nowrap;
        }}
        
        th, td {{
            padding: 16px 18px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background-color: var(--table-header);
            color: var(--table-header-text);
            font-weight: 600;
        }}
        
        tr:hover td {{
            background-color: var(--row-hover);
        }}
        
        .no-data {{
            text-align: center;
            color: var(--text-muted);
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 آخرین قیمت‌های استخراج شده</h1>
            <div class="update-time">به‌روزرسانی: {now_shamsi}</div>
            <br>
            <!-- فیلد جستجوی پیشرفته -->
            <input type="text" id="searchInput" class="search-box" placeholder="جستجو در تمام اطلاعات جداول (سایز، برند و...)" onkeyup="filterCards()">
        </header>
        <main id="cardsContainer">
            {sections_html}
        </main>
    </div>

    <!-- اسکریپت فیلتر حرفه‌ای سطر به سطر -->
    <script>
        function filterCards() {{
            let input = document.getElementById('searchInput').value.toLowerCase();
            let cards = document.getElementsByClassName('card');
            
            for (let i = 0; i < cards.length; i++) {{
                let card = cards[i];
                let titleText = card.querySelector('.card-header h2').innerText.toLowerCase();
                let rows = card.querySelectorAll('table tr');
                
                let hasVisibleRow = false;
                let titleMatch = titleText.includes(input); // اگر اسم خود کادر جستجو شد

                // بررسی تک‌تک سطرهای جدول
                for (let j = 0; j < rows.length; j++) {{
                    let row = rows[j];
                    
                    // از مخفی کردن تیترهای جدول (ردیف‌های دارای th) جلوگیری می‌کنیم
                    if (row.querySelector('th')) {{
                        continue;
                    }}
                    
                    let rowText = row.innerText.toLowerCase();
                    
                    // اگر کلمه در این سطر بود، یا اینکه کاربر اسم کل کادر را سرچ کرده بود
                    if (titleMatch || rowText.includes(input)) {{
                        row.style.display = ""; // نمایش سطر
                        hasVisibleRow = true;
                    }} else {{
                        row.style.display = "none"; // پنهان کردن سطر
                    }}
                }}
                
                // اگر حتی یک سطر پیدا شد، کل کادر را نشان بده، در غیر این صورت کل کادر پنهان شود
                if (titleMatch || hasVisibleRow) {{
                    card.style.display = "";
                }} else {{
                    card.style.display = "none";
                }}
            }}
        }}
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

def main():
    if not os.path.exists("data"):
        os.makedirs("data")
        
    all_results = []
    for source in SOURCES:
        tables = fetch_tables_from_url(source["url"])
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
