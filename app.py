import os
import re
import subprocess
import tempfile
import shutil
import json
from pathlib import Path

import anthropic
import chainlit as cl
import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader

# ─── Config ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DOCS_DIR = "docs"
OUTPUTS_DIR = "outputs"

MODEL_SMART = "claude-opus-4-6"          # Für CV & Motivationsschreiben
MODEL_FAST = "claude-haiku-4-5-20251001"  # Für Analyse & einfache Tasks

SYSTEM_PROMPT = """Du bist ein Experten-Coach für Karriereberatung, spezialisiert auf Senior-Rollen
im Bereich Data Science, Analytics und Marketing-Strategie.

Deine Aufgabe ist es, Flavio Caderas dabei zu unterstützen, herausragende Bewerbungsunterlagen zu erstellen.

PROFIL FLAVIO CADERAS:
Letzte Position: Data Science Analytics Manager (Customer Marketing Analytics) bei eBay Marketplaces GmbH (2019–2025)
USP: Komplexe Datenanalysen durch klare Kommunikation verständlich machen, um fundierte Entscheidungen zu ermöglichen.

SCHREIBSTIL-RICHTLINIEN:
- Kein Füllmaterial, keine Phrasen wie "motivierter Teamplayer"
- Konkrete Resultate mit Begriffen wie "Business Impact", "Conversion-Optimierung", "Marketingeffizienz"
- Tonfall: Professionell, selbstbewusst, direkt
- Moderne Tech-Unternehmenssprache
- Prägnante Bullet Points statt langer Fliesstext
- Keine Zitate, keine Bindestriche im Fliesstext"""


# ─── Helper Functions ─────────────────────────────────────────────────────────

def load_documents():
    """Lädt alle Dokumente aus dem docs/ Ordner."""
    docs_path = Path(DOCS_DIR)
    content = ""

    for pdf_file in docs_path.glob("*.pdf"):
        try:
            loader = PyPDFLoader(str(pdf_file))
            pages = loader.load()
            for page in pages:
                content += f"\n\n[Aus {pdf_file.name}]:\n{page.page_content}"
        except Exception as e:
            print(f"❌ Fehler bei {pdf_file.name}: {e}")

    for txt_file in docs_path.glob("*.txt"):
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                content += f"\n\n[Aus {txt_file.name}]:\n{f.read()}"
        except Exception as e:
            print(f"❌ Fehler bei {txt_file.name}: {e}")

    return content


def load_latex_template(filename):
    """Lädt einen LaTeX Template aus docs/."""
    template_path = Path(DOCS_DIR) / filename
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def scrape_job_description(url):
    """Scraped eine Stellenbeschreibung von einer URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line for line in text.split("\n") if line.strip()]
        return "\n".join(lines[:200])
    except Exception as e:
        return f"Fehler beim Laden der URL: {e}"


def extract_company_name(client, job_description):
    """Extrahiert den Firmennamen aus der Stellenbeschreibung."""
    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"Extrahiere nur den Firmennamen aus dieser Stellenbeschreibung. Antworte mit NUR dem Firmennamen, nichts anderes:\n\n{job_description[:2000]}"
        }]
    )
    name = response.content[0].text.strip()
    # Sonderzeichen entfernen für Dateinamen
    name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    return name if name else "Unbekannt"


def analyze_matching(client, profile_data, job_description):
    """Analysiert den Match zwischen Profil und Stelle."""
    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Analysiere den Match zwischen Flavios Profil und dieser Stelle.

STELLENBESCHREIBUNG:
{job_description}

FLAVIOS PROFIL:
{profile_data[:3000]}

Antworte NUR mit einem JSON Objekt in diesem Format:
{{
  "gesamt_score": 85,
  "staerken": [
    {{"skill": "Data Science", "score": 95}},
    {{"skill": "A/B Testing", "score": 90}},
    {{"skill": "Stakeholder Management", "score": 85}}
  ],
  "gaps": [
    {{"skill": "Scala", "score": 0}},
    {{"skill": "AWS", "score": 20}}
  ],
  "empfehlung": "Kurze Empfehlung ob Flavio sich bewerben soll"
}}"""
        }]
    )

    try:
        text = response.content[0].text.strip()
        # JSON aus Response extrahieren
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass

    return {
        "gesamt_score": 80,
        "staerken": [{"skill": "Data Science", "score": 90}],
        "gaps": [],
        "empfehlung": "Gute Übereinstimmung mit der Stelle."
    }


def format_matching_message(matching):
    """Formatiert die Matching-Analyse als schöne Nachricht."""
    score = matching.get("gesamt_score", 0)

    if score >= 80:
        emoji = "🟢"
        bewertung = "Sehr guter Match!"
    elif score >= 60:
        emoji = "🟡"
        bewertung = "Guter Match"
    else:
        emoji = "🔴"
        bewertung = "Schwacher Match"

    msg = f"## 📊 Matching Analyse\n\n"
    msg += f"### {emoji} Gesamt-Match: **{score}%** – {bewertung}\n\n"

    if matching.get("staerken"):
        msg += "**✅ Stärken:**\n"
        for s in matching["staerken"]:
            bar = "█" * (s["score"] // 10) + "░" * (10 - s["score"] // 10)
            msg += f"- {s['skill']}: {bar} {s['score']}%\n"

    if matching.get("gaps"):
        msg += "\n**⚠️ Gap Analyse:**\n"
        for g in matching["gaps"]:
            msg += f"- {g['skill']}: {g['score']}% (im CV nicht stark vertreten)\n"

    if matching.get("empfehlung"):
        msg += f"\n**💡 Empfehlung:** {matching['empfehlung']}"

    return msg


def generate_cv_latex(client, profile_data, job_description, cv_template):
    """Generiert angepassten CV LaTeX Code."""
    response = client.messages.create(
        model=MODEL_SMART,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "ccontent": f"""Passe den LaTeX CV Template für diese Stelle an.

STELLENBESCHREIBUNG:
{job_description}

PROFIL & DOKUMENTE:
{profile_data}

LATEX CV TEMPLATE:
{cv_template}

STRIKTE REGELN – NIEMALS VERÄNDERN:
1. Sektionsreihenfolge EXAKT beibehalten wie im Template
2. Alle Daten/Jahreszahlen/Monate EXAKT wie im Template übernehmen
3. "Sabbatical & Persönliche Projekte" IMMER beibehalten
4. "Berufliche Neuorientierung" IMMER an gleicher Position
5. Tabellenspaltenbreite p{{3.8cm}} NIEMALS ändern
6. Dateinamen von Bildern EXAKT übernehmen (profile_photo.png)
7. Struktur, Formatierung und LaTeX-Befehle NICHT verändern

NUR ERLAUBT:
- Profiltext (Zusammenfassung oben) anpassen
- Bullet Points in Berufserfahrung anpassen
- Titel/Untertitel falls direkt zur Stelle passend

Erstelle einen angepassten LaTeX CV der:
1. Die relevantesten Erfahrungen für diese Stelle hervorhebt
2. Keywords aus der Stellenbeschreibung natürlich einbaut
3. Messbare Erfolge und Business Impact betont

Gib NUR den LaTeX Code zurück, ohne Erklärungen oder Markdown-Backticks."""
        }]
    )
    return response.content[0].text


def generate_cover_letter_latex(client, profile_data, job_description, cl_template):
    """Generiert Motivationsschreiben LaTeX Code."""
    response = client.messages.create(
        model=MODEL_SMART,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Erstelle ein überzeugendes Motivationsschreiben im LaTeX Format.

STELLENBESCHREIBUNG:
{job_description}

PROFIL & DOKUMENTE:
{profile_data}

LATEX MOTIVATIONSSCHREIBEN TEMPLATE:
{cl_template}

Erstelle ein Motivationsschreiben das:
1. Direkt auf die spezifischen Anforderungen der Stelle eingeht
2. Flavios USP hervorhebt
3. Konkrete Beispiele aus der eBay-Zeit nennt
4. Professionell, selbstbewusst und direkt ist

Gib NUR den LaTeX Code zurück, ohne Erklärungen oder Markdown-Backticks."""
        }]
    )
    return response.content[0].text


def compile_latex_to_pdf(latex_code, output_filename):
    """Kompiliert LaTeX Code zu PDF."""
    output_dir = Path(OUTPUTS_DIR)
    output_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = Path(tmpdir) / "document.tex"

        # Profilbild kopieren
        photo_path = Path(DOCS_DIR) / "profile_photo.png"
        if photo_path.exists():
            shutil.copy(photo_path, Path(tmpdir) / "profile_photo.png")

        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_code)

        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "document.tex"],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

        pdf_source = Path(tmpdir) / "document.pdf"
        pdf_dest = output_dir / output_filename

        if pdf_source.exists():
            shutil.copy(pdf_source, pdf_dest)
            return str(pdf_dest)
        else:
            print("LaTeX Fehler:", result.stdout[-2000:])
            return None


# ─── Chainlit App ─────────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start():
    if not ANTHROPIC_API_KEY:
        await cl.Message(
            content="⚠️ **ANTHROPIC_API_KEY fehlt!**\n```bash\nexport ANTHROPIC_API_KEY=sk-ant-...\n```"
        ).send()
        return

    await cl.Message(
        content="""# 🎯 Job Application Agent

Ich bin dein persönlicher Karriere-Coach und erstelle massgeschneiderte Bewerbungsunterlagen.

**Was ich mache:**
- 📊 Matching Score & Gap Analyse
- 📄 Angepasstes CV als PDF
- ✍️ Motivationsschreiben als PDF
- 🎉 Abschluss-Zusammenfassung

**So funktioniert es:**
Gib mir einfach die URL der Stellenausschreibung – optional mit Kommentaren.

**Beispiel:**
```
https://www.linkedin.com/jobs/view/123456
Ich möchte besonders meine KI-Erfahrung hervorheben.
```

Bereit? Los geht's! 🚀"""
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    if not ANTHROPIC_API_KEY:
        await cl.Message(content="⚠️ API Key fehlt!").send()
        return

    # URL extrahieren
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message.content)

    if not urls:
        await cl.Message(
            content="⚠️ Keine URL gefunden! Bitte gib die URL der Stellenausschreibung ein.\n\nBeispiel: `https://www.linkedin.com/jobs/view/123456`"
        ).send()
        return

    job_url = urls[0]
    extra_comments = message.content.replace(job_url, "").strip()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ── Schritt 1: Job laden ──────────────────────────────────────────────────
    msg = cl.Message(content="🔍 **Schritt 1/4** – Lade Stellenbeschreibung...")
    await msg.send()

    job_description = scrape_job_description(job_url)
    if extra_comments:
        job_description += f"\n\nZUSÄTZLICHE KOMMENTARE:\n{extra_comments}"

    # Firmenname extrahieren
    company_name = extract_company_name(client, job_description)

    # ── Schritt 2: Matching Analyse ───────────────────────────────────────────
    msg.content = "📊 **Schritt 2/4** – Analysiere Match..."
    await msg.update()

    profile_data = load_documents()
    cv_template = load_latex_template("cv_template.tex")
    cl_template = load_latex_template("cover_letter_template.tex")

    matching = analyze_matching(client, profile_data, job_description)

    # Matching anzeigen
    await cl.Message(content=format_matching_message(matching)).send()

    # ── Schritt 3: Dokumente generieren ───────────────────────────────────────
    msg2 = cl.Message(content="📄 **Schritt 3/4** – Erstelle CV...")
    await msg2.send()

    cv_latex = generate_cv_latex(client, profile_data, job_description, cv_template)

    msg2.content = "✍️ **Schritt 3/4** – Erstelle Motivationsschreiben..."
    await msg2.update()

    cl_latex = generate_cover_letter_latex(client, profile_data, job_description, cl_template)

    # ── Schritt 4: PDFs kompilieren ───────────────────────────────────────────
    msg2.content = "⚙️ **Schritt 4/4** – Kompiliere PDFs..."
    await msg2.update()

    cv_filename = f"CV_{company_name}.pdf"
    cl_filename = f"Motivationsschreiben_{company_name}.pdf"

    cv_pdf = compile_latex_to_pdf(cv_latex, cv_filename)
    cl_pdf = compile_latex_to_pdf(cl_latex, cl_filename)

    # LaTeX Code speichern
    Path(OUTPUTS_DIR).mkdir(exist_ok=True)
    with open(f"{OUTPUTS_DIR}/CV_{company_name}.tex", "w") as f:
        f.write(cv_latex)
    with open(f"{OUTPUTS_DIR}/Motivationsschreiben_{company_name}.tex", "w") as f:
        f.write(cl_latex)

    # ── Abschluss-Nachricht ───────────────────────────────────────────────────
    score = matching.get("gesamt_score", 0)
    gaps = matching.get("gaps", [])
    gap_text = ""
    if gaps:
        gap_names = [g["skill"] for g in gaps]
        gap_text = f"\n\n💡 **Tipp:** Erwähne in der Bewerbung wie du diese Skills aufbaust: {', '.join(gap_names)}"

    abschluss = f"""## 🎉 Deine Bewerbung für **{company_name.replace('_', ' ')}** ist bereit!

📄 `CV_{company_name}.pdf`
📝 `Motivationsschreiben_{company_name}.pdf`

**Match Score: {score}%** {"🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"}
{gap_text}

Viel Erfolg bei deiner Bewerbung! 🍀"""

    await cl.Message(content=abschluss).send()

    # PDFs als Download anbieten
    elements = []
    if cv_pdf and Path(cv_pdf).exists():
        elements.append(cl.File(name=cv_filename, path=cv_pdf, display="inline"))
    if cl_pdf and Path(cl_pdf).exists():
        elements.append(cl.File(name=cl_filename, path=cl_pdf, display="inline"))

    if elements:
        await cl.Message(
            content="📎 **Hier sind deine Dokumente:**",
            elements=elements
        ).send()
