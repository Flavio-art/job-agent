# 🎯 Job Application Agent

An AI-powered career coach that generates tailored CV and cover letter PDFs from a job posting URL — in seconds.

Built with Claude (Anthropic API), Chainlit, and LaTeX.

---

## ✨ What It Does

Paste a job URL into the chat. The agent will:

1. **Scrape** the job description automatically
2. **Analyse** your profile match with a scoring breakdown
3. **Generate** a tailored CV in LaTeX, compiled to PDF
4. **Write** a professional cover letter, compiled to PDF
5. **Deliver** both documents named after the company (e.g. `CV_Google.pdf`)

---

## 📊 Matching Score & Gap Analysis

Before generating any documents, the agent evaluates how well your profile fits the role:

```
📊 Matching Analysis

🟢 Overall Match: 87% — Strong Fit

✅ Strengths:
- Data Science:           ██████████  95%
- A/B Testing:            █████████░  90%
- Stakeholder Management: ████████░░  85%

⚠️ Gap Analysis:
- Scala:  not represented in CV
- AWS:    20% coverage

💡 Recommendation: Strong candidate. Emphasise AI adoption experience.
```

---

## 🏗️ Architecture

```
Job URL (input)
      ↓
 Web Scraper (BeautifulSoup)
      ↓
 Profile Documents (docs/)
 ├── CV Template (.tex)
 ├── Cover Letter Template (.tex)
 ├── Reference Letter (.pdf)
 └── Personal Notes (.txt)
      ↓
 personal_config.py (private, not on GitHub)
 ├── SYSTEM_PROMPT       → Career coaching persona
 ├── CV_GENERATION_PROMPT → CV rules & guidelines
 ├── COVER_LETTER_PROMPT  → Cover letter guidelines
 └── MATCHING_PROMPT      → Match scoring logic
      ↓
 Claude API
 ├── Haiku  →  Matching Score & Gap Analysis
 └── Opus   →  CV & Cover Letter Generation
      ↓
 LaTeX Compiler (pdflatex)
      ↓
 PDF Output (outputs/)
 ├── CV_CompanyName.pdf
 └── Motivationsschreiben_CompanyName.pdf
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11
- [LaTeX / MacTeX](https://www.tug.org/mactex/) for PDF compilation
- An [Anthropic API Key](https://console.anthropic.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/Flavio-art/job-agent.git
cd job-agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Install LaTeX (macOS)

```bash
brew install --cask basictex
eval "$(/usr/libexec/path_helper)"
```

### Set your API Key

```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-your-key-here' >> ~/.zshrc
source ~/.zshrc
```

### Create your personal config

Create a `personal_config.py` file in the project root (this file is private and not on GitHub):

```python
SYSTEM_PROMPT = """You are an expert career coach...
[your personal coaching prompt here]
"""

CV_GENERATION_PROMPT = """..."""
COVER_LETTER_PROMPT = """..."""
MATCHING_PROMPT = """..."""
```

See `personal_config.example.py` for the full template.

### Add your documents

```
docs/
├── cv_template.tex           ← Your LaTeX CV template
├── cover_letter_template.tex ← Your LaTeX cover letter template
├── profile_photo.png         ← Profile photo (referenced in CV)
├── personal_notes.txt        ← Skills, preferences, context for the agent
└── reference_letter.pdf      ← Optional: work reference
```

### Run the agent

```bash
chainlit run app.py
```

Open **http://localhost:8000** in your browser.

---

## 💬 Usage

Simply paste a job URL into the chat — with optional comments:

```
https://www.linkedin.com/jobs/view/123456789
Please emphasise my AI and RAG experience for this role.
```

The agent handles the rest.

---

## 💰 Cost Estimate

| Step | Model | Approx. Cost |
|---|---|---|
| Matching Analysis | claude-haiku-4-5 | ~$0.01 |
| CV Generation | claude-opus-4-6 | ~$0.09 |
| Cover Letter | claude-opus-4-6 | ~$0.09 |
| **Total per application** | | **~$0.19** |

$5 in API credits ≈ 25 tailored applications.

---

## 📁 Project Structure

```
job-agent/
├── app.py                    ← Main Chainlit app & agent logic
├── personal_config.py        ← Your private prompts (NOT on GitHub)
├── personal_config.example.py← Template to create your own config
├── requirements.txt          ← Python dependencies
├── .gitignore                ← Excludes docs/, outputs/, personal_config.py
├── docs/                     ← Your private documents (not on GitHub)
└── outputs/                  ← Generated PDFs (not on GitHub)
```

---

## 🔒 Privacy

This project is designed with privacy in mind:

```
On GitHub:          NOT on GitHub:
─────────────────   ──────────────────────
app.py              personal_config.py  ← Your prompts & profile
requirements.txt    docs/               ← Your CV templates & documents
README.md           outputs/            ← Generated PDFs
.gitignore          .env                ← API keys
```

Your documents and personal prompts never leave your machine unless sent to the Anthropic API for generation. No data is stored by this application.

---

## 🛠️ Tech Stack

- [Chainlit](https://chainlit.io) — Chat UI
- [Anthropic Claude](https://anthropic.com) — AI generation
- [LangChain](https://langchain.com) — Document loading
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) — Job scraping
- [LaTeX / pdflatex](https://www.latex-project.org) — PDF compilation

---

## 🗺️ Roadmap

- [ ] Interview preparation questions
- [ ] Auto-detect language from job posting
- [ ] Draft application email
- [ ] WhatsApp integration
- [ ] Docker support

---

Built by [Flavio Caderas](https://github.com/Flavio-art) · Powered by Claude
