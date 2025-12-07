from config import Config
import re
from typing import List
from bs4 import BeautifulSoup
from utils import logger

def ConvertTeacherToStudent(teacher_html: str) -> List[str]:
    """Konvertiert einen Lehrerplan (HTML-String) in eine Liste von Schülerplänen (HTML-Strings).
    
    Lieste den Inhalt von 'plan_style.html', extrahiert den Inhalt aller 
    <body>-Tags aus dem Eingabestring und fügt ihn mit dem Header und dem abschließenden 
    '</html>'-Tag zu vollständigen HTML-Dokumenten zusammen.
    
    Args:
        teacher_html: Der komplette HTML-String des Lehrerplans.

    Returns:
        Eine Liste von HTML-Strings, wobei jeder String ein vollständiger Schülerplan ist.
    """
    
    # 1. Lese den Inhalt von 'plan_style.html' (muss im selben Verzeichnis liegen)
    file_path = 'plan_style.html'
    template_header = ""
    
    try:
        # Annahme: plan_style.html enthält den HTML-Header bis einschließlich des öffnenden <body>-Tags.
        with open(file_path, 'r', encoding='utf-8') as f:
            # Entferne eventuelle Whitespaces am Ende, falls der Body-Tag direkt am Ende steht
            template_header = f.read().strip() 
    except FileNotFoundError:
        # Wichtiger Hinweis: Ohne diese Datei kann die Konvertierung nicht funktionieren.
        print(f"Fehler: Die Vorlagendatei '{file_path}' wurde nicht gefunden.")
        return []
    except Exception as e:
        print(f"Fehler beim Lesen der Datei '{file_path}': {e}")
        return []

    # 2. Definiere den abschließenden Tag
    # Wir fügen </body> hinzu, um wohlgeformtes HTML zu gewährleisten, da der Header mit <body> endet.
    template_footer = '\n\n</body>\n</html>'
    
    # 3. Regulärer Ausdruck zur Extraktion des Inhalts zwischen <body> und </body> (nicht-gierig)
    # re.DOTALL ist notwendig, damit '.' über Zeilenumbrüche hinweg matched.
    body_content_pattern = re.compile(r'<body.*?>(.*?)</body>', re.IGNORECASE | re.DOTALL)
    
    # Finde alle Übereinstimmungen und extrahiere den Inhalt
    body_contents = body_content_pattern.findall(teacher_html)
    
    # 4. Erstelle die neuen HTML-Strings
    student_plans: List[str] = []
    
    for content in body_contents:
        # Aufbau: template_header (enthält <body>) + extrahierter_Inhalt + template_footer (enthält </body></html>)
        # Die trim-Operation stellt sicher, dass unnötige Whitespaces um den Inhalt entfernt werden.
        new_plan = template_header + content.strip() + template_footer
        student_plans.append(new_plan)
        
    #return student_plans
    
    transformed_plans = [_restructure_mon_list_table(plan) for plan in student_plans]
    return transformed_plans





import re
from bs4 import BeautifulSoup

def _restructure_mon_list_table(html_string: str) -> str:
    NEW_HEADERS = ["Klasse(n)", "Stunde", "Vertreter", "(Lehrer)", "Fach", "Raum", "(Fach)", "Art", "Text"]
    SPECIAL_CLASSES = {"E1", "E2", "Q1", "Q2", "Q3", "Q4", "AG"}  # AG jetzt ans Ende
    ALLOWED_ART = {
        "Vertretung",
        "Entfall",
        "Lehrertausch",
        "Verlegung",
        "Unterricht geändert",
        "Sondereins.",
        "Raum-Vtr.",
        "Tausch"
    }

    try:
        soup = BeautifulSoup(html_string, 'html.parser')
        mon_list_table = soup.find('table', class_='mon_list')

        if not mon_list_table:
            return html_string

        # Füge tbody hinzu, falls nicht vorhanden
        old_tbody = mon_list_table.find('tbody')
        if not old_tbody:
            old_tbody = soup.new_tag('tbody')
            for tr in mon_list_table.find_all('tr', recursive=False):
                old_tbody.append(tr.extract())
            mon_list_table.append(old_tbody)

        # Tabelle in Array von Arrays extrahieren
        all_rows = old_tbody.find_all('tr', recursive=False)
        table_data = []
        for row in all_rows:
            cells = row.find_all(['td', 'th'], recursive=False)
            row_data = [cell.get_text(strip=True) for cell in cells]
            table_data.append(row_data)

        # Filter: nur erlaubte Art
        data_rows = table_data[1:]  # Header ausschließen
        data_rows = [
            row for row in data_rows
            if len(row) >= 8 and row[7] in ALLOWED_ART
        ]
        # Zeilen müssen genügend Spalten für Mapping haben
        data_rows = [row for row in data_rows if len(row) >= max([2,1,0,5,3,4,3,7,8])+1]

        # Sortieren nach Original-Klasse (Spalte 2)
        def klassen_key(row):
            klasse = row[2].replace("(", "").replace(")", "").strip()
            if not klasse or klasse == "":
                return (float('inf'), float('inf'), klasse)  # leere Klasse ans Ende
            if klasse in {"E1","E2","Q1","Q2","Q3","Q4","AG"}:
                return (float('inf'), klasse, klasse)  # Sonderklassen ans Ende
            match = re.match(r"(\d+)?([a-zA-Z]*)", klasse)
            if match:
                num_part = int(match.group(1)) if match.group(1) else 0
                letter_part = match.group(2)
                return (num_part, letter_part, klasse)
            return (float('inf'), klasse, klasse)

        data_rows.sort(key=klassen_key)

        # Neuen Table Body aufbauen
        new_tbody = soup.new_tag('tbody')

        # Header hinzufügen
        new_header_row = soup.new_tag('tr', **{'class': 'list'})
        for header_text in NEW_HEADERS:
            th = soup.new_tag('th', align='center', **{'class': 'list'})
            if header_text == "Klasse(n)":
                b_tag = soup.new_tag('b')
                b_tag.string = header_text
                th.append(b_tag)
            else:
                th.string = header_text
            new_header_row.append(th)
        new_tbody.append(new_header_row)

        # Datenzeilen aufbauen
        COLUMN_MAPPING = [2, 1, 0, 5, 3, 4, 3, 7, 8]  # Mapping der Spalten
        for idx, row_data in enumerate(data_rows):
            tr_class = "list odd" if idx % 2 == 0 else "list even"
            new_row = soup.new_tag('tr', **{'class': tr_class})
            for col_idx, i in enumerate(COLUMN_MAPPING):
                td = soup.new_tag('td', **{'class': 'list', 'align': 'center'})

                # Bei Art "Entfall" bestimmte Spalten auf "---" setzen
                if row_data[7] == "Entfall" and col_idx in [2,4,5]:  # neue Spalten 2,4,5
                    cell_text = "---"
                else:
                    cell_text = row_data[i]

                # Fett für Klasse(n) (erste Spalte nach Mapping)
                if col_idx == 0:
                    b_tag = soup.new_tag('b')
                    b_tag.string = cell_text
                    td.append(b_tag)
                else:
                    td.string = cell_text

                new_row.append(td)
            new_tbody.append(new_row)

        old_tbody.decompose()
        mon_list_table.append(new_tbody)
        return str(soup)

    except Exception as e:
        return html_string
