"""Constants extracted from SKILL.md, research-quality-reviewer.md, and v12.17 pipeline."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
SUBAGENT_PROMPTS_DIR = PROJECT_ROOT / "subagent_prompts"
ECOMTORIALS_ROOT = PROJECT_ROOT.parent  # D:/kmuautomation/ecomtorials

# CrossRef
CROSSREF_MAILTO = "research@digierf.de"
CROSSREF_BASE_URL = "https://api.crossref.org"
CROSSREF_TIMEOUT = 30

# Perplexity
PERPLEXITY_AGENT_URL = "https://api.perplexity.ai/v1/agent"
PERPLEXITY_CHAT_URL = "https://api.perplexity.ai/chat/completions"

# Perplexity Agent API presets (multi-step reasoning + web_search + fetch_url)
PERPLEXITY_PRESETS = {
    "fast-search": {"model": "xai/grok-4-1-fast", "max_steps": 1, "tools": ["web_search"]},
    "pro-search": {"model": "openai/gpt-5.1", "max_steps": 3, "tools": ["web_search", "fetch_url"]},
    "deep-research": {"model": "openai/gpt-5.2", "max_steps": 10, "tools": ["web_search", "fetch_url"]},
}

# Academic domain whitelist
ACADEMIC_DOMAINS = [
    "scholar.google.com", "semanticscholar.org", "doaj.org",
    "sciencedirect.com", "link.springer.com", "onlinelibrary.wiley.com",
    "tandfonline.com", "academic.oup.com", "cambridge.org", "nature.com",
    "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "ieeexplore.ieee.org",
    "jstor.org", "dl.acm.org", "arxiv.org", "ssrn.com",
    "researchgate.net", "biorxiv.org", "medrxiv.org", "plos.org", "science.org",
]

# Quality thresholds
QUALITY_THRESHOLD = 7.0
MAX_REPAIR_ITERATIONS = 1
MAX_QUALITY_ITERATIONS = 2

# Phase 0 Safety Lock
SAFETY_LOCK_THRESHOLD = 0.4  # 40% token match required

# R1 Categories (25) — Block A-I structure from v12.17
# name, min, p1, effective_min
R1_CATEGORIES = {
    # Block A: Produkt
    "01": {"name": "Produktdetails",                        "min": 3, "p1": True,  "eff_min": 4,  "block": "A"},
    "02": {"name": "Strategische Limitierungen",            "min": 3, "p1": False, "eff_min": 3,  "block": "A"},
    "03": {"name": "Hauptwirkstoffe & USPs",                "min": 3, "p1": True,  "eff_min": 4,  "block": "A"},
    # Block B: Zielgruppe
    "04": {"name": "Zielmarkt",                             "min": 3, "p1": True,  "eff_min": 4,  "block": "B"},
    "05": {"name": "Identität & Tribe-Zugehörigkeit",       "min": 3, "p1": True,  "eff_min": 4,  "block": "B"},
    # Block C: Schmerzpunkte
    "06": {"name": "Hauptschmerzpunkte (körperlich)",       "min": 5, "p1": True,  "eff_min": 7,  "block": "C"},
    "07": {"name": "Emotionale Schmerzpunkte",              "min": 5, "p1": True,  "eff_min": 7,  "block": "C"},
    "08": {"name": "Konkrete Problemvarianten",             "min": 5, "p1": False, "eff_min": 5,  "block": "C"},
    "09": {"name": "Ursache des Problems (Root Cause)",     "min": 5, "p1": False, "eff_min": 5,  "block": "C"},
    "10": {"name": "Trigger-Events & Auslöser",             "min": 5, "p1": True,  "eff_min": 7,  "block": "C"},
    # Block D: Lösungen
    "11": {"name": "Fehlgeschlagene Lösungen",              "min": 5, "p1": False, "eff_min": 5,  "block": "D"},
    "12": {"name": "Konkurrenzangebote",                    "min": 5, "p1": False, "eff_min": 5,  "block": "D"},
    # Block E: Wettbewerb
    "13": {"name": "Market Sophistication (Schwartz)",      "min": 5, "p1": True,  "eff_min": 7,  "block": "E"},
    "14": {"name": "Konkurrenz-Claims & Messaging",         "min": 5, "p1": True,  "eff_min": 7,  "block": "E"},
    # Block F: Ziele
    "15": {"name": "Wünsche und Ziele",                     "min": 5, "p1": False, "eff_min": 5,  "block": "F"},
    "16": {"name": "Wunschzustand (Future Pacing)",         "min": 5, "p1": False, "eff_min": 5,  "block": "F"},
    "17": {"name": "Werte und Vision",                      "min": 5, "p1": False, "eff_min": 5,  "block": "F"},
    # Block G: Vorteile
    "18": {"name": "Funktionaler Vorteil",                  "min": 5, "p1": False, "eff_min": 5,  "block": "G"},
    "19": {"name": "Emotionaler Vorteil",                   "min": 5, "p1": False, "eff_min": 5,  "block": "G"},
    # Block H: Barrieren
    "20": {"name": "Typische Einwände",                     "min": 5, "p1": False, "eff_min": 5,  "block": "H"},
    "21": {"name": "Emotionale Kaufängste",                 "min": 3, "p1": False, "eff_min": 3,  "block": "H"},
    "22": {"name": "Mythen & falsche Überzeugungen",        "min": 5, "p1": False, "eff_min": 5,  "block": "H"},
    # Block I: Proof
    "23": {"name": "Social Proof & Nutzerzahlen",           "min": 3, "p1": False, "eff_min": 3,  "block": "I"},
    "24": {"name": "Aussagekräftige Kundenbewertungen",     "min": 10, "p1": True, "eff_min": 15, "block": "I"},
    "25": {"name": "Studien & Credibility",                 "min": 5, "p1": False, "eff_min": 5,  "block": "I"},
}

# R2 Categories (8) — unchanged
R2_CATEGORIES = {
    "1": {"name": "Physical Problem",                     "min": 5, "p1": False, "eff_min": 5},
    "2": {"name": "Emotional Problem",                    "min": 5, "p1": False, "eff_min": 5},
    "3": {"name": "Failed Solutions (Toxische Skepsis)",  "min": 5, "p1": True,  "eff_min": 7},
    "4": {"name": "Belief Breaks (Originalsprache)",      "min": 5, "p1": True,  "eff_min": 7},
    "5": {"name": "Physical Benefit",                     "min": 5, "p1": False, "eff_min": 5},
    "6": {"name": "Emotional Benefit",                    "min": 5, "p1": False, "eff_min": 5},
    "7": {"name": "Aha-Moment",                           "min": 3, "p1": False, "eff_min": 3},
    "8": {"name": "Wunschzustand",                        "min": 5, "p1": False, "eff_min": 5},
}

# Ingredient quality filters
BANNED_INGREDIENTS = [
    "natürlich", "naturrein", "premium", "hochdosiert", "laborgeprüft",
    "bio-zertifiziert", "vegan", "glutenfrei", "ohne Zusätze", "rein pflanzlich",
    "dermatologisch getestet", "klinisch erprobt", "hochwirksam", "einzigartig",
    "revolutionär", "innovativ", "traditionell", "altbewährt", "hauteigen",
    "evidenzbasiert", "wohltuend", "revitalisierend", "regenerierend", "synergie",
    "ganzheitlich", "kraftvoll", "intensiv", "pflegend",
]

TOO_GENERIC_INGREDIENTS = [
    "Lipide", "Fettsäuren", "Vitamine", "Mineralstoffe", "Aminosäuren",
    "Antioxidantien", "Enzyme", "Probiotika", "Präbiotika", "Kollagen", "Peptide",
    "Extrakt", "Öle", "Nährstoffe", "Spurenelemente", "Proteine",
]

# Lifestyle-Domains — bei Perplexity Agent API als Denylist (Prefix "-")
# Entspricht Tier E in source_rules.md
PERPLEXITY_BLOCKED_DOMAINS = [
    "-wunderweib.de",
    "-brigitte.de",
    "-fit-for-fun.de",
    "-bild.de",
    "-bunte.de",
    "-gala.de",
    "-freundin.de",
    "-cosmopolitan.de",
]

# Perplexity Agent API instructions (injected into every preset call)
PERPLEXITY_INSTRUCTIONS = (
    "Antworte auf Deutsch. "
    "Bevorzuge Fachportale, Testmagazine und institutionelle Quellen. "
    "Vermeide Lifestyle-Blogs als Beleg für faktische Claims. "
    "Gib für jede Aussage die direkte URL an."
)

# Theory domain blocking (for Kat. 14 Konkurrenz-Claims)
THEORY_BLOCKED_DOMAINS = [
    "elitemarketingpro.com",
    "swipefile.com",
    "motiveinmotion.com",
    "nordiccopy.com",
    "copyblogger.com",
]

# Anti-Hallucination: Synthetic review detection patterns (v12.17)
AI_REVIEW_PATTERNS = [
    "Zusammenfassend lässt sich sagen",
    "Basierend auf meiner Erfahrung",
    "Ich kann nur empfehlen",
    "Alles in allem",
    "Man merkt sofort",
    "Ich bin absolut begeistert",
    "Das Produkt hält was es verspricht",
    "Ich habe schon viele Produkte ausprobiert",
    "Nach nur wenigen Tagen",
    "Ich kann es jedem empfehlen",
    "Das Preis-Leistungs-Verhältnis ist hervorragend",
    "Meine Erwartungen wurden übertroffen",
]

# Anti-Hallucination: LLM filler patterns to remove in post-processing (v12.17)
LLM_FILLER_PATTERNS = [
    "Basierend auf den bereitgestellten Daten",
    "Laut meiner Recherche",
    "Zusammenfassend lässt sich sagen",
    "Leider habe ich keinen Zugriff in Echtzeit",
    "Es ist wichtig zu beachten, dass",
    "Wie bereits erwähnt",
    "Basierend auf den verfügbaren Informationen",
    "Es sei darauf hingewiesen",
    "Im Folgenden werden",
    "Abschließend lässt sich festhalten",
    "Wie oben beschrieben",
    "Laut den vorliegenden Daten",
]

# Quality reviewer weights (13 checks, v12.17 upgrade)
QUALITY_WEIGHTS = {
    "Q1":  2.0,   # Quellenabdeckung
    "Q2":  2.0,   # Kategorien-Vollständigkeit (25 Kat.)
    "Q3":  1.5,   # Belief Architecture
    "Q4":  2.0,   # Studien-Qualität
    "Q5":  1.5,   # Zitat-Authentizität
    "Q6":  1.0,   # Zeichenlimit
    "Q7":  1.0,   # Wirkstoff-Fokus
    "Q8":  1.5,   # UMP/UMS 3-Kriterien
    "Q9":  1.0,   # Zwei-Ebenen-Beweis
    "Q10": 1.5,   # Konsistenz R1↔R3
    "Q11": 1.5,   # Meta-Regeln Alignment
    "Q12": 1.0,   # Cross-Contamination (Sibling/Nische)
    "Q13": 0.5,   # LLM Filler (0 Filler-Phrasen)
}
QUALITY_WEIGHT_TOTAL = 18.0

# Agent defaults
DEFAULT_MODEL = "sonnet"
MAX_TURNS = 200
MAX_BUDGET_USD = 20.0
