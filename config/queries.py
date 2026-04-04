"""
config/queries.py
-----------------
Curated query set for Claude discourse discovery.

Design principles:
- Cover branded terms (Claude AI, Claude 3.7, Sonnet, Opus, Haiku)
- Cover competitive angle (Claude vs ChatGPT, Claude vs GPT-4)
- Cover use-case angles (coding, workflow, prompt, writing)
- Cover sentiment/narrative angles (opinion, review, benchmark)
- Cover growth signals (viral moment, creator demo, tutorial)
- Keep queries tight enough to be relevant, broad enough to surface organic posts
"""

# ── Primary brand queries ──────────────────────────────────────────────────────
BRAND_QUERIES = [
    "Claude AI",
    "Anthropic Claude",
    "Claude claude.ai",
    "Claude LLM",
]

# ── Model-specific queries ─────────────────────────────────────────────────────
MODEL_QUERIES = [
    "Claude 3.7",
    "Claude 3.7 Sonnet",
    "Claude 3 Sonnet",
    "Claude 3 Opus",
    "Claude 3 Haiku",
    "Claude 3.5 Sonnet",
    "Claude 4",  # forward-looking chatter
    "Claude Sonnet",
    "Claude Opus",
    "Claude Haiku",
]

# ── Competitive / comparison queries ──────────────────────────────────────────
COMPARISON_QUERIES = [
    "Claude vs ChatGPT",
    "Claude vs GPT-4",
    "Claude vs GPT-4o",
    "Claude vs Gemini",
    "Claude vs Grok",
    "Claude better than ChatGPT",
    "ChatGPT vs Claude",
    "switch to Claude",
    "moved from ChatGPT to Claude",
]

# ── Use-case / workflow queries ────────────────────────────────────────────────
USECASE_QUERIES = [
    "Claude coding",
    "Claude for coding",
    "Claude code generation",
    "Claude workflow",
    "Claude writing assistant",
    "Claude for work",
    "Claude productivity",
    "Claude automation",
    "Claude API",
    "Claude computer use",
    "Claude artifacts",
    "Claude canvas",
]

# ── Prompt / technique queries ─────────────────────────────────────────────────
PROMPT_QUERIES = [
    "Claude prompt",
    "Claude prompt engineering",
    "Claude system prompt",
    "Claude jailbreak",  # captures controversy/viral discourse
    "Claude refuses",  # captures safety discourse
    "Claude uncensored",  # controversy signal
    "how to use Claude",
    "Claude tips",
    "Claude tricks",
]

# ── Tutorial / educational queries ────────────────────────────────────────────
TUTORIAL_QUERIES = [
    "Claude tutorial",
    "Claude guide",
    "Claude how to",
    "learn Claude AI",
    "Claude for beginners",
    "Claude demo",
    "Claude walkthrough",
]

# ── Benchmark / performance queries ───────────────────────────────────────────
BENCHMARK_QUERIES = [
    "Claude benchmark",
    "Claude MMLU",
    "Claude reasoning",
    "Claude intelligence",
    "Claude beats",
    "Claude outperforms",
    "Claude smartest AI",
    "Claude best model",
]

# ── Opinion / review / experience queries ─────────────────────────────────────
OPINION_QUERIES = [
    "Claude review",
    "Claude honest review",
    "Claude experience",
    "Claude worth it",
    "Claude subscription",
    "Claude Pro",
    "Claude free tier",
    "Claude disappointed",
    "love Claude",
    "hate Claude",
    "Claude changed my workflow",
]

# ── Viral / meme / cultural queries ───────────────────────────────────────────
VIRAL_QUERIES = [
    "Claude moment",
    "Claude surprised me",
    "Claude hallucination",
    "Claude funny",
    "Claude meme",
    "Anthropic",
    "Dario Amodei",  # founder discourse = brand growth signal
]

# ── News / announcement queries ───────────────────────────────────────────────
NEWS_QUERIES = [
    "Claude launched",
    "Anthropic released",
    "Claude update",
    "Claude new feature",
    "Claude announcement",
    "Anthropic funding",
    "Anthropic valuation",
]

# ── All queries combined ───────────────────────────────────────────────────────
ALL_QUERIES = (
    BRAND_QUERIES
    + MODEL_QUERIES
    + COMPARISON_QUERIES
    + USECASE_QUERIES
    + PROMPT_QUERIES
    + TUTORIAL_QUERIES
    + BENCHMARK_QUERIES
    + OPINION_QUERIES
    + VIRAL_QUERIES
    + NEWS_QUERIES
)

# ── Query groups for targeted collection ──────────────────────────────────────
# Use these to run focused collection passes without repeating everything
QUERY_GROUPS = {
    "brand": BRAND_QUERIES,
    "model": MODEL_QUERIES,
    "comparison": COMPARISON_QUERIES,
    "usecase": USECASE_QUERIES,
    "prompt": PROMPT_QUERIES,
    "tutorial": TUTORIAL_QUERIES,
    "benchmark": BENCHMARK_QUERIES,
    "opinion": OPINION_QUERIES,
    "viral": VIRAL_QUERIES,
    "news": NEWS_QUERIES,
}

# ── Per-platform recommended query subsets ────────────────────────────────────
# YouTube: longer, educational, demo-heavy → tutorials + benchmarks + reviews
YOUTUBE_PRIORITY_GROUPS = ["tutorial", "benchmark", "opinion", "comparison", "usecase"]

# X/Twitter: real-time, opinion, comparisons, viral moments
X_PRIORITY_GROUPS = ["brand", "comparison", "viral", "opinion", "news", "model"]

# TikTok/Reddit/Threads: discovery only, short queries work best
SUPPLEMENTAL_PRIORITY_GROUPS = ["brand", "comparison", "viral", "tutorial"]
