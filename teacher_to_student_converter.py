from config import Config
import re
from typing import List

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
        
    return student_plans