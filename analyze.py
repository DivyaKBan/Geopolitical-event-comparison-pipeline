import time
from typing import Literal

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError

from config import MODEL_NAME

load_dotenv()
llm = Groq(timeout=60.0, max_retries=1)

EventType = Literal["diplomacy", "conflict", "sanctions_trade", "politics_elections",
                    "energy", "security", "humanitarian", "other"]

class Claim(BaseModel):
    claim: str
    sources: list[int]

class SourceView(BaseModel):
    source: int
    says: str

class Difference(BaseModel):
    topic: str
    views: list[SourceView]

class EventAnalysis(BaseModel):
    same_event: bool
    event_title: str
    summary: str
    countries: list[str]
    event_type: EventType
    agreed_facts: list[Claim]
    differences: list[Difference]

SYSTEM = """You compare news reports about one event. You receive numbered articles (outlet, headline, short snippet).
Rules:
- Use ONLY the text provided. Add no outside knowledge.
- Set same_event to false if the articles describe different events.
- agreed_facts: facts stated by at least two articles. List the article numbers.
- differences: details where outlets give different numbers, wording, causes or emphasis. State them neutrally.
  Never say an outlet is biased, wrong or propaganda.
- If the snippets are too short to compare, return an empty differences list.
- summary: 2-3 neutral sentences.
- event_title must be built only from words in the headlines. Do not add years, dates or names that do not appear in the articles.
- Every item in summary, agreed_facts and differences must be supported by the numbered articles.
- event_type must be one of: diplomacy, conflict, sanctions_trade, politics_elections, energy, security, humanitarian, other.
Return ONLY a JSON object with keys: same_event, event_title, summary, countries, event_type, agreed_facts, differences.
agreed_facts items: {"claim": "...", "sources": [1, 2]}
differences items: {"topic": "...", "views": [{"source": 1, "says": "..."}]}"""

def pick_articles(group, limit=8):
    seen, first, rest = set(), [], []
    for a in group:
        (rest if a["source"] in seen else first).append(a)
        seen.add(a["source"])
    return (first + rest)[:limit]

def build_prompt(articles):
    return "\n\n".join(
        f"[{i}] Outlet: {a['source']}\nHeadline: {a['title']}\nSnippet: {a['snippet']}"
        for i, a in enumerate(articles, start=1)
    )

def extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end != -1 else text

def analyze(articles, retries=4):
    prompt = build_prompt(articles)
    max_tokens, json_mode = 1500, True
    for attempt in range(retries):
        try:
            kwargs = dict(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
                extra_body={"reasoning_effort": "low"},   # delete this line if Groq rejects it
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = llm.chat.completions.create(**kwargs)
            text = (resp.choices[0].message.content or "").strip()
            if not text:                      # reasoning models can use the whole budget thinking
                max_tokens = min(max_tokens * 2, 6000)
                continue
            return EventAnalysis.model_validate_json(extract_json(text))
        except ValidationError as e:
            print("  invalid JSON from model, retrying:", str(e)[:100])
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "timed out" in msg:
                time.sleep(2 ** attempt * 5)
            elif "response_format" in msg:
                json_mode = False
            else:
                print("  LLM error:", str(e)[:200])
                return None
    return None

def clean_analysis(result, n):
    """Drop citations that point to article numbers that don't exist, and claims with fewer than 2 sources."""
    kept, dropped = [], 0
    for c in result.agreed_facts:
        nums = sorted({s for s in c.sources if 1 <= s <= n})
        if len(nums) >= 2:
            c.sources = nums
            kept.append(c)
        else:
            dropped += 1
    result.agreed_facts = kept
    for d in result.differences:
        d.views = [v for v in d.views if 1 <= v.source <= n]
    result.differences = [d for d in result.differences if len(d.views) >= 2]
    return result, dropped