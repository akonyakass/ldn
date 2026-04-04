"""
pipeline/labeler.py
--------------------
Assigns content_category and author_type labels to each row.

Design goals:
  - Shrink "other" to < 15% of rows
  - Use keyword-based rules first (fast, transparent, reproducible)
  - Rules are ordered: first match wins (order matters)
  - All rules are lowercase-matched against: title + text_snippet combined

CONTENT CATEGORIES
──────────────────
  comparison_vs_chatgpt   "vs chatgpt", "vs gpt", "switch from", "better than"
  benchmark_claim         "benchmark", "mmlu", "beats", "outperforms", "score"
  tutorial_how_to         "how to", "tutorial", "guide", "step by step", "learn"
  creator_demo            "demo", "walkthrough", "showing", "watch me", "i tried"
  workflow_use_case       "workflow", "productivity", "automation", "for work", "use case"
  news_announcement       "launch", "release", "update", "announced", "new feature", "funding"
  opinion_discussion      "opinion", "think", "honest", "worth it", "review", "experience"
  experience_story        "changed my", "i switched", "i moved", "story", "journey", "day"
  meme_humor              "lol", "lmao", "funny", "meme", "😂", "😭", "💀"
  product_review          "review", "subscription", "pro plan", "free tier", "pricing"
  prompt_engineering      "prompt", "system prompt", "context window", "tokens"
  safety_controversy      "refuse", "jailbreak", "censored", "blocked", "bias"
  other                   (fallback)

CONTRIBUTOR TYPES
─────────────────
  company                 known company handles: anthropic, openai, google, microsoft...
  creator_blogger         YouTube channel keywords, Substack, blog-style handles
  developer               GitHub, dev.to references, "engineer", "developer", "coder"
  media                   known media handles: techcrunch, verge, wired, forbes...
  community_user          reddit usernames (u/...), low-follower patterns
  unknown                 (fallback)
"""

import re
import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ── Content category rules ──────────────────────────────────────────────────────
# Each rule is (category_name, list_of_keyword_patterns)
# Order matters: first match wins.
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    # ── Claude Code / agentic coding (must come FIRST — very high volume) ──────
    (
        "claude_code_agentic",
        [
            r"\bclaude\s+code\b",
            r"\bclaude\s+coding\b",
            r"\bcoding\s+with\s+claude\b",
            r"\bcode\s+w/\s*claude\b",
            r"\bvibecod(e|ing)\b",
            r"\bclaude\s+agent\b",
            r"\bagentic\s+(coding|ai)\b",
            r"\bollama\s*\+\s*claude\b",
        ],
    ),
    # ── Tool / platform comparisons (Cursor, Copilot, Replit, etc.) ───────────
    (
        "tool_comparison",
        [
            r"\bcursor\s+vs\b",
            r"\bvs\.?\s*cursor\b",
            r"\breplit\s+vs\b",
            r"\bvs\.?\s*replit\b",
            r"\blovable\s+vs\b",
            r"\bvs\.?\s*lovable\b",
            r"\bcopilot\s+vs\b",
            r"\bvs\.?\s*copilot\b",
            r"\bcodex\s+vs\b",
            r"\bvs\.?\s*codex\b",
            r"\bwindsurf\s+vs\b",
            r"\bvs\.?\s*windsurf\b",
            r"\bclaude\s+vs\s+cursor\b",
            r"\bi\s+tested\s+them\b",
            r"\bwhich\s+(is\s+)?(better|best|#1)\b",
        ],
    ),
    (
        "comparison_vs_chatgpt",
        [
            r"vs\.?\s*chatgpt",
            r"vs\.?\s*gpt[-\s]?4",
            r"vs\.?\s*gpt[-\s]?4o",
            r"vs\.?\s*gemini",
            r"vs\.?\s*grok",
            r"vs\.?\s*mistral",
            r"vs\.?\s*openai",
            r"switch(ed|ing)?\s+(from|to)\s+chatgpt",
            r"chatgpt\s+vs\.?\s+claude",
            r"better\s+than\s+chatgpt",
            r"moved\s+from\s+chatgpt",
            r"move\s+from\s+chatgpt",
            r"from\s+chatgpt\s+to\s+claude",
        ],
    ),
    (
        "benchmark_claim",
        [
            r"\bbenchmark\b",
            r"\bmmlu\b",
            r"\bgsm8k\b",
            r"\bhuman ?eval\b",
            r"\bbeats\b.{0,30}(gpt|gemini|llm|openai|codex)",
            r"\boutperform",
            r"\bscored?\b.{0,20}(higher|lower|better)",
            r"\bintelligence\s+score",
            r"\bsmartest\b",
            r"\bbest\s+model\b",
            r"\bstate.of.the.art\b",
            r"\bsota\b",
            r"\breason(ing)?\s+(test|score|benchmark)\b",
        ],
    ),
    (
        "tutorial_how_to",
        [
            r"\bhow\s+to\b",
            r"\btutorial\b",
            r"\bguide\b",
            r"\bstep.by.step\b",
            r"\blearn\s+(to\s+use|claude)\b",
            r"\bfor\s+beginners\b",
            r"\bwalkthrough\b",
            r"\bquick\s+start\b",
            r"\bgetting\s+started\b",
            r"\bexplained\b",
            r"\bclearly\s+explained\b",
            r"\b\d+\s+(minutes?|mins?|hours?)\s+of\b",
            r"\blessons?\s+in\b",
            r"\bmaster(ing)?\s+claude\b",
            r"\bcomplete\s+(guide|course|overview)\b",
        ],
    ),
    (
        "creator_demo",
        [
            r"\bdemo\b",
            r"\bwatch\s+me\b",
            r"\bi\s+tried\b",
            r"\bi\s+tested\b",
            r"\bshowing\b",
            r"\bhands.on\b",
            r"\btest(ing|ed)?\s+claude\b",
            r"\bplay(ing)?\s+(with|around with)\s+claude\b",
            r"\bi\s+showed\b",
            r"\blet('?s)?\s+try\b",
            r"\bfirst\s+look\b",
            r"\bmy\s+(first|honest)\s+(time|try|attempt)\b",
        ],
    ),
    (
        "workflow_use_case",
        [
            r"\bworkflow\b",
            r"\bproductiv(ity|e)\b",
            r"\bautomation\b",
            r"\bfor\s+(work|business|writing|coding)\b",
            r"\buse\s+case\b",
            r"\bday.to.day\b",
            r"\bbuilt\s+(with|using)\s+claude\b",
            r"\bclaude\s+(api|computer\s+use|artifacts)\b",
            r"\bpipeline\b",
            r"\bn8n\b",
            r"\bmake\.com\b",
            r"\bzapier\b",
            r"\baddicted\s+to\s+claude\b",
            r"\bclaude\s+on\s+your\s+(phone|mobile|iphone)\b",
        ],
    ),
    (
        "news_announcement",
        [
            r"\blaunch(ed|es)?\b",
            r"\brelease[sd]?\b",
            r"\bannounced?\b",
            r"\bunveil(s|ed)?\b",
            r"\bnew\s+(feature|model|version|update)\b",
            r"\bfunding\b",
            r"\bvaluation\b",
            r"\binvest(ment|ed|or)\b",
            r"\bbreaking\b",
            r"\bexclusiv(e|ely)\b",
            r"\breport(s|ed)?\b.{0,20}(anthropic|claude)",
            r"\btrump\b.{0,20}(claude|anthropic|ai)",
            r"anthropic\s+(unveil|releas|announc|drop)",
        ],
    ),
    (
        "earn_money_business",
        [
            r"\bmake\s+\$",
            r"\b\$\$\$\b",
            r"\bearn(ing)?\s+(money|\$)",
            r"\bmake\s+money\b",
            r"\bpassive\s+income\b",
            r"\bskills?\s+(will\s+make\s+you|pays?)\b",
            r"\bfreelance\b",
            r"\bside\s+hustle\b",
            r"\bai\s+business\b",
            r"\bmonetize\b",
        ],
    ),
    (
        "meme_humor",
        [
            r"\blol\b",
            r"\blmao\b",
            r"\bfunny\b",
            r"\bmeme\b",
            r"😂",
            r"😭",
            r"💀",
            r"🤣",
            r"\bwtf\b",
            r"\bbruh\b",
            r"\bvibes?\b",
            r"hallucin(at|ation)",
            r"\bsurprised?\s+me\b",
        ],
    ),
    (
        "safety_controversy",
        [
            r"\brefus(es?|ed|ing)\b",
            r"\bjailbreak\b",
            r"\bcensored?\b",
            r"\bbias(ed)?\b",
            r"\bblocked?\b",
            r"\bsafety\b.{0,30}claude",
            r"\buncensored\b",
            r"\baligned?\b",
            r"\bAI\s+safety\b",
        ],
    ),
    (
        "prompt_engineering",
        [
            r"\bprompt\b",
            r"\bsystem\s+prompt\b",
            r"\bcontext\s+window\b",
            r"\btokens?\b",
            r"\bprompt\s+engin(eering|eer)\b",
            r"\binstruction\s+following\b",
            r"\bfew.shot\b",
            r"\bchain.of.thought\b",
        ],
    ),
    (
        "experience_story",
        [
            r"\bchanged\s+my\b",
            r"\bi\s+switched\b",
            r"\bmy\s+(journey|story|experience)\b",
            r"\bi\s+(moved|started\s+using|been\s+using)\b",
            r"\bpersonal\b.{0,20}(story|take|experience)",
            r"\bsharing\s+my\b",
        ],
    ),
    (
        "product_review",
        [
            r"\breview\b",
            r"\bsubscription\b",
            r"\bpro\s+plan\b",
            r"\bfree\s+tier\b",
            r"\bpricing\b",
            r"\bworth\s+(it|the\s+money)\b",
            r"\bhonest\s+(review|opinion|take)\b",
            r"\bpros?\s+and\s+cons?\b",
            r"\brating\b",
        ],
    ),
    (
        "opinion_discussion",
        [
            r"\bopinion\b",
            r"\bthink(ing|s)?\b.{0,20}claude",
            r"\bdiscuss(ion|ing)?\b",
            r"\bdebate\b",
            r"\bperspective\b",
            r"\bwhat\s+do\s+you\s+think\b",
            r"\btake\b.{0,10}on\s+claude",
            r"\bi\s+(believe|think|feel)\b",
        ],
    ),
]

FALLBACK_CATEGORY = "other"

# ── Contributor type rules ─────────────────────────────────────────────────────
COMPANY_HANDLES = {
    "anthropic",
    "openai",
    "google",
    "microsoft",
    "meta",
    "amazon",
    "apple",
    "nvidia",
    "huggingface",
    "mistralai",
    "cohere",
    "deepmind",
    "xai",
    "perplexity",
}

MEDIA_HANDLES = {
    "techcrunch",
    "theverge",
    "wired",
    "forbes",
    "venturebeat",
    "businessinsider",
    "cnbc",
    "reuters",
    "bloomberg",
    "nytimes",
    "washingtonpost",
    "guardian",
    "engadget",
    "arstechnica",
    "zdnet",
    "pcmag",
    "tomshardware",
    "theatlantic",
}

DEVELOPER_PATTERNS = [
    r"\bdev(eloper)?\b",
    r"\bengineer\b",
    r"\bcoder\b",
    r"\bprogrammer\b",
    r"\bsoftware\b",
    r"github\.com",
    r"dev\.to",
    r"\btech\b.{0,10}(blog|writer)",
]

CREATOR_PATTERNS = [
    r"\bai\s+(news|weekly|daily|update)\b",
    r"\b(tech|ai)\s+(channel|creator|youtuber)\b",
    r"\bsubstack\b",
    r"\bnewsletter\b",
    r"\btutorials?\b",
    r"\breviews?\s+channel\b",
]


def _classify_category(text: str) -> str:
    text_lower = text.lower()
    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return category
    return FALLBACK_CATEGORY


def _classify_author_type(handle: str, title: str = "", snippet: str = "") -> str:
    if not handle:
        return "unknown"
    handle_lower = handle.lower()
    text_lower = (title + " " + snippet).lower()

    # Company check (exact handle match)
    for company in COMPANY_HANDLES:
        if company in handle_lower:
            return "company"

    # Media check
    for media in MEDIA_HANDLES:
        if media in handle_lower:
            return "media"

    # Developer patterns (in handle or bio-style text)
    for pat in DEVELOPER_PATTERNS:
        if re.search(pat, handle_lower) or re.search(pat, text_lower):
            return "developer"

    # Creator/blogger patterns
    for pat in CREATOR_PATTERNS:
        if re.search(pat, handle_lower) or re.search(pat, text_lower):
            return "creator_blogger"

    # Reddit community user pattern (u/username style)
    if handle_lower.startswith("u/") or handle_lower.startswith("/u/"):
        return "community_user"

    return "unknown"


def label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add/overwrite content_category and author_type columns.

    Args:
        df: Normalized DataFrame with title, text_snippet, author_handle columns.

    Returns:
        DataFrame with content_category and author_type filled in.
    """
    df = df.copy()

    # Combine title + text_snippet for classification
    combined_text = df["title"].fillna("") + " " + df["text_snippet"].fillna("")

    df["content_category"] = combined_text.apply(_classify_category)
    df["author_type"] = df.apply(
        lambda r: _classify_author_type(
            str(r.get("author_handle", "") or ""),
            str(r.get("title", "") or ""),
            str(r.get("text_snippet", "") or ""),
        ),
        axis=1,
    )

    # Log distribution
    cat_dist = df["content_category"].value_counts()
    auth_dist = df["author_type"].value_counts()
    logger.info(f"[Labeler] Content categories:\n{cat_dist}")
    logger.info(f"[Labeler] Author types:\n{auth_dist}")

    return df


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "data/normalized/combined.csv"
    df = pd.read_csv(path)
    df = label(df)
    df.to_csv(path, index=False)
    print(df["content_category"].value_counts())
