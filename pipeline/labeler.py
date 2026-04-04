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
  off_topic               Mobile Legends game, anime characters named Claude (not Claude AI)
  claude_code_agentic     Claude Code IDE, vibe coding, agentic AI coding
  claude_features         Claude Cowork, Skills, MCP, Artifacts, model names (Sonnet/Opus/Haiku)
  tool_comparison         Cursor vs, Copilot vs, Replit vs (coding tool comparisons)
  comparison_vs_chatgpt   vs ChatGPT, vs Gemini, switch from ChatGPT
  switching_to_claude     switching/moving to Claude, cancelling ChatGPT
  benchmark_claim         benchmark, MMLU, beats GPT, outperforms, SOTA
  tutorial_how_to         how to, tutorial, guide, crash course, from zero to
  creator_demo            demo, I tried, I tested, I accidentally, I asked Claude
  workflow_use_case       workflow, productivity, automation, AI stack, SaaS tools
  news_announcement       launched, leaked, outage, OpenClaw ban, Anthropic news
  earn_money_business     make $, startup revenue, two employees, AI business
  meme_humor              Claude-specific humor only: "claude lol", AI hallucination jokes
  safety_controversy      refuse, jailbreak, censored, bias, FBI, dangerous AI
  prompt_engineering      prompt, system prompt, context window, tokens
  experience_story        changed my, my story, AGI moment, one thing to say
  product_review          review, pricing, worth it, better deal, expensive
  opinion_discussion      opinion, everyone is talking, nobody is talking, AI narrative
  other                   (fallback — genuinely unclassifiable)

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
    # ── OFF-TOPIC: Claude as game/anime character (Mobile Legends, Who Made Me a Princess) ──
    # Must come FIRST to prevent all downstream misclassification
    (
        "off_topic",
        [
            r"\bmobile\s*legends?\b",
            r"\bmlbb\b",
            r"\bml\s+build\b",
            r"\bemblem\b.{0,20}(build|claude)",
            r"\bgold\s+lane\b",
            r"\bwho\s+made\s+me\s+a\s+princess\b",
            r"\bathanasia\b",
            r"\bde\s+alger\s+obelia\b",
            r"\bnijisanji\b",
            r"\bvtuber\b",
            r"\banime\s+(edit|amv|clip)\b",
            r"\bkuroshitsuji\b",
            r"\bgta\s+(san|5|6|iv)\b",
            r"\bdnd\b",
            r"\bttrpg\b",
            r"\bslow\s+horses?\b",
            r"\bvox\s+vanta\b",
        ],
    ),
    # ── Claude Code / agentic coding (must come early — very high volume) ──────
    (
        "claude_code_agentic",
        [
            r"\bclaude\s+code\b",
            r"\bclaude\s+coding\b",
            r"\bcoding\s+with\s+claude\b",
            r"\bcode\s+w/\s*claude\b",
            r"\bvibe\s*cod(e|ing)\b",
            r"\bclaude\s+agent\b",
            r"\bagentic\s+(coding|ai)\b",
            r"\bollama\s*\+\s*claude\b",
            r"\bai\s+cod(e|ing|ed)\b",
            r"\bbuilt?\s+(an?\s+)?(app|game|tool|website|bot)\s+(with|using|in)\s+(claude|ai)\b",
            r"\bclaude\s+(built|created|wrote|generated)\b",
            r"\bi\s+(built|made|created)\s+.{0,30}(claude|ai)\b",
        ],
    ),
    # ── Claude-specific NEW features: Cowork, Skills, MCP, Artifacts ──────────
    (
        "claude_features",
        [
            r"\bclaude\s+cowork\b",
            r"\bclaude\s+skills?\b",
            r"\bmodel\s+context\s+protocol\b",
            r"\bmcp\b.{0,20}(claude|anthropic)",
            r"\bclaude\s+artifacts?\b",
            r"\bclaude\s+computer\s+use\b",
            r"\bclaude\s+max\b",
            r"\bclaude\s+mythos\b",
            r"\bclaude\s+opus\s+[34]\b",
            r"\bclaude\s+sonnet\b",
            r"\bclaude\s+haiku\b",
            r"\bclaude\s+3\.[5-9]\b",
            r"\bclaude\s+[34]\b",
            r"\bnew\s+claude\b",
            r"\bclaude's\s+(latest|newest|new)\b",
            r"\banthropics?\s+(new|latest)\b",
            r"\bclaude\s+api\b",
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
            r"vs\.?\s*gpt[-\s]?5",
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
            r"chatgpt\s+(or|over)\s+claude",
            r"claude\s+(or|over)\s+chatgpt",
        ],
    ),
    # ── Switching to Claude (decision/advocacy content) ───────────────────────
    (
        "switching_to_claude",
        [
        r"\bswitch(ing|ed)?\s+to\s+claude\b",
        r"\bmov(ing|ed)\s+to\s+claude\b",
        r"\bcancel\s+(chatgpt|openai|gpt)\b",
        r"\bleav(ing|e)\s+(chatgpt|openai)\b",
        r"\bdump(ed|ing)?\s+chatgpt\b",
        r"\bquitt?ing\s+(chatgpt|openai)\b",
        r"\btime\s+to\s+switch\b",
        r"\bnow\s+is\s+a\s+great\s+time\b.{0,30}claude",
        r"\bdone\s+with\s+(chatgpt|openai)\b",
        r"\bi'?m\s+done\.?\s*(switching|moving|leaving)\b",
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
            r"\bmatches?\s+(performance|score)\b",
            r"\bat\s+less\s+than\s+\d+%\s+of\s+the\s+cost\b",
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
            r"\bfor\s+beginners?\b",
            r"\bwalkthrough\b",
            r"\bquick\s+start\b",
            r"\bgetting\s+started\b",
            r"\bexplained\b",
            r"\bclearly\s+explained\b",
            r"\b\d+\s+(minutes?|mins?|hours?)\s+(of|to|course)\b",
            r"\blessons?\s+in\b",
            r"\bmaster(ing)?\s+claude\b",
            r"\bcomplete\s+(guide|course|overview)\b",
            r"\bcrash\s+course\b",
            r"\bfrom\s+(zero|scratch|beginner)\s+to\b",
            r"\bin\s+\d+\s+(minutes?|seconds?)\b",
            r"\beverything\s+you\s+need\s+to\s+know\b",
            r"\bfull\s+course\b",
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
            r"\bi\s+accidentally\b",
            r"\bwhat\s+happens?\s+if\b",
            r"\bi\s+asked\s+claude\b",
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
            r"\bdangerously\s+produc\b",
            r"\bai\s+employee\b",
            r"\bai\s+agent\s+(that|which|to)\b",
            r"\bai\s+stack\b",
            r"\bai\s+tools?\s+(you|for|i|we)\b",
            r"\bsaas\b.{0,30}(claude|ai|founder)",
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
            r"\bleaked?\b.{0,30}(claude|anthropic)",
            r"\banthropics?\s+left\b",
            r"\boutage\b",
            r"\bdown\b.{0,20}(claude|anthropic)",
            r"\banthropic\s+ban(ned|s)\b",
            r"\bopen\s?claw\b",
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
            r"\b\$\d+(k|m|,\d{3})\b.{0,30}(claude|ai)",
            r"\bmillion\b.{0,30}(claude|ai|built)",
            r"\bstartup\b.{0,30}(claude|ai|built|chatgpt)",
            r"\btwo\s+employees?\b",
            r"\bbuilt\s+.{0,20}million\b",
        ],
    ),
    # ── Meme/humor: ONLY fire on Claude-AI-specific humor signals ─────────────
    # Removed generic emoji traps (😭💀) — those catch anime/gaming content
    (
        "meme_humor",
        [
            r"\bclaude\b.{0,60}(lol|lmao|wtf|bruh|�|🤣|�😂)",
            r"(lol|lmao|wtf|bruh|�|🤣|😂).{0,60}\bclaude\b",
            r"\banthropics?\b.{0,60}(lol|lmao|funny|meme|wtf)",
            r"\bclaude\b.{0,40}\bfunny\b",
            r"\bclaude\b.{0,40}\bmeme\b",
            r"\bai\s+(meme|humor|joke|funny)\b",
            r"\bhallucin(at|ation).{0,40}(claude|ai)",
            r"(claude|ai).{0,40}\bhallucin(at|ation)\b",
            r"\bclaude\s+hold\s+my\s+beer\b",
            r"\bclaude\b.{0,30}\bwtf\b",
            r"\bi\s+accidentally\s+turned\s+claude\b",
            r"\bclaude\s+is\s+(unhinged|wild|unplayable|cooked|based|based)\b",
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
            r"\balign(ed|ment)?\b",
            r"\bAI\s+safety\b",
            r"\bcontact(ed)?\s+the\s+fbi\b",
            r"\bdangerous\s+ai\b",
            r"\bmost\s+dangerous\b.{0,20}(claude|ai)",
            r"\bpartnered\s+with\b.{0,20}(military|pentagon|palantir)",
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
            r"\bone\s+thing\s+to\s+say\b",
            r"\bagi\s+moment\b",
            r"\bthis\s+is\s+the\s+(moment|future)\b",
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
            r"\bexpensive\b.{0,20}(claude|ai)",
            r"\bcheaper\b.{0,20}(claude|ai)",
            r"\bbetter\s+deal\b",
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
            r"\beveryone\s+is\s+talking\s+about\b",
            r"\bnobody\s+is\s+talking\b",
            r"\bpeople\s+miss\b",
            r"\breal\s+story\b",
            r"\bnarrative\s+was\s+a\s+lie\b",
            r"\bai\s+is\s+(replacing|not\s+replacing)\b",
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
    # handle-level signals
    r"_dev\b",
    r"\bdev_",
    r"_coder\b",
    r"_builds?\b",
    r"_codes?\b",
    r"\bbuilds?\b",
    r"writes?\s+code",
    r"\bstack\b",  # Better Stack, Full Stack, etc.
    r"\bfullstack\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bhacker\b",
    r"\bml\b",
    r"\bllm\b",
    r"\bcloud\b",
    r"\bopen.?source\b",
]

CREATOR_PATTERNS = [
    r"\bai\s+(news|weekly|daily|update)\b",
    r"\b(tech|ai)\s+(channel|creator|youtuber)\b",
    r"\bsubstack\b",
    r"\bnewsletter\b",
    r"\btutorials?\b",
    r"\breviews?\s+channel\b",
    # YouTube channel name patterns: "Name | Topic" or "Name with Topic"
    r"\|\s*(ai|tech|code|coding|automation|seo|learn)",
    r"\bwith\s+(ai|claude|code|kyle|nate)\b",
    # Common creator keywords in channel names
    r"\bai\s+(automation|academy|mastery|simplified|explained|lab|hub|tips)\b",
    r"\b(learn|mastering|teaching)\s+(ai|code|coding|python|tech)\b",
    r"\b(ai|tech|code|coding|seo)\s+(with|by|from)\b",
    r"\bnever\s+code\s+alone\b",
    r"\bcaleb\b",
    r"\bcole\s+medin\b",
    r"\bnate\s+herk\b",
    r"\bkyle\s+balmer\b",
    r"\bjulian\s+goldie\b",
    r"\bleon\s+van\s+zyl\b",
    r"\bgeorge\s+ai\b",
    r"\bmedul\b",
    # AI/tech newsletter / blog patterns
    r"\baim\s+network\b",
    r"\btraction\b",
    r"\bstudio\b",
    r"\b(tech|ai|code)\s*bytes?\b",
    # X/Twitter creator signals in handle
    r"ramonov",
    r"sabrina_",
    r"_ai\b",
    r"\bai_",
]


def _classify_category(text: str) -> str:
    text_lower = text.lower()
    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return category
    return FALLBACK_CATEGORY


def _classify_author_type(
    handle: str, title: str = "", snippet: str = "", platform: str = ""
) -> str:
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

    # Reddit: u/username style OR platform=reddit with random-looking handle
    if handle_lower.startswith("u/") or handle_lower.startswith("/u/"):
        return "community_user"
    if platform == "reddit":
        # Reddit handles with numbers, underscores, or mixed-case random patterns
        # are almost always regular community users
        return "community_user"

    # X/YouTube: if handle has "ai", "tech", "code" etc. → creator_blogger (catch-all)
    if re.search(
        r"(ai|tech|code|coding|coder|build|hack|dev|learn|teach)", handle_lower
    ):
        return "creator_blogger"

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
            str(r.get("source_platform", "") or ""),
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
