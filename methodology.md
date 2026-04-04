# Data Methodology Note
## Claude Viral Growth Playbook — HackNU 2026

---

## 1. Trust Tier System

This project uses a **two-tier data trust model** to ensure analytical integrity.

### Tier 1 — High-Trust Quantitative Sources
| Source | Access Method | Metrics Available |
|---|---|---|
| YouTube Data API v3 | Official API key | views, likes, comments, published_at |
| X (Twitter) API v2 | Bearer token | impressions, likes, replies, retweets, quotes |

**Why these are trusted:**  
Both platforms return structured JSON via authenticated API calls.  
Metrics are official platform counts, not scraped estimates.  
All numeric fields (views, likes, etc.) are integers with clear semantics.  
Date fields are ISO 8601 timestamps from the platform itself.  
These rows carry `trust_tier = "tier1_api"` and `metric_reliability = "high"`.

**Primary use:** All quantitative analysis, engagement rate calculations,
cross-platform comparisons, and growth trend modelling use Tier 1 data exclusively.

---

### Tier 2 — Supplemental Public-Page Sources
| Source | Access Method | Metrics Available |
|---|---|---|
| TikTok | SERP discovery + public HTML | Sometimes: views, likes via JSON-LD or regex |
| Reddit | Public `/search.json` endpoint | score (upvotes), num_comments, created_utc |
| Threads | SERP discovery + public HTML | Title + description only |

**Why these are supplemental:**  
Metrics are extracted from public HTML metadata, which varies by page render state.  
TikTok pages sometimes expose viewCount/diggCount in embedded JSON — when present, we capture them.  
Reddit's public JSON is moderately reliable for score/comments, but has no impression count.  
Threads exposes no engagement metrics at all in public HTML.  
None of these sources require login, API keys, or any anti-bot circumvention.

These rows carry `trust_tier = "tier2_public_page"` and `metric_reliability = "low"` by default.  
TikTok rows where views were successfully extracted are upgraded to `metric_reliability = "medium"`.

**Primary use:** Narrative discovery (what topics are being discussed),
qualitative signal for which content formats and talking points appear across platforms.
NOT used as primary evidence for engagement rankings or growth metrics.

---

## 2. Engagement Definition

Engagement is defined consistently across all platforms as:

```
engagement = likes + comments + reposts_shares
```

Where:
- **YouTube**: likes + comments (no reposts concept)
- **X**: likes + replies + (retweets + quotes)
- **TikTok**: likes + 0 (comments and reposts not reliably available from public HTML)
- **Reddit**: score + num_comments (score ≈ upvotes minus downvotes)
- **Threads**: all None (no metrics available)

**Engagement rate** is only computed when views exist:
```
engagement_rate = engagement / views    (Tier 1 only)
```

This is left as `null` for any row without a reliable view count.

---

## 3. Deduplication Strategy

1. First pass: deduplicate by `(post_id, source_platform)` — same post collected by multiple queries
2. Second pass: deduplicate by canonical URL — removes mobile/desktop URL variants
3. Cross-platform duplicates are KEPT intentionally — the same content appearing on multiple
   platforms is itself a viral distribution signal worth measuring

When duplicates exist, priority is:
- Tier 1 rows over Tier 2 rows
- Rows with more metrics populated over rows with fewer

---

## 4. Content Labeling

Labels are assigned by keyword-rule matching on `title + text_snippet`.  
Rules are ordered — first match wins.  
The category set is designed to minimize the "other" bucket to < 15% of rows.

**Content categories** (13 total):
`comparison_vs_chatgpt`, `benchmark_claim`, `tutorial_how_to`, `creator_demo`,
`workflow_use_case`, `news_announcement`, `meme_humor`, `safety_controversy`,
`prompt_engineering`, `experience_story`, `product_review`, `opinion_discussion`, `other`

**Author types** (6 total):
`company`, `creator_blogger`, `developer`, `media`, `community_user`, `unknown`

Author types are inferred from handle matching against known company/media lists
and developer/creator keyword patterns. This is best-effort and should be treated
as indicative, not definitive.

---

## 5. Selective Scaling Principle

This project deliberately avoids blind scaling. The guiding principle is:

> **More rows with no usable metrics make the dataset noisier, not richer.**

Scaling decisions:
- ✅ Increase YouTube and X volume — every row has reliable metrics
- ✅ Expand query coverage (more query variants, not just more pages per query)
- ⚠️ Moderately expand TikTok/Reddit — only when metrics are extractable
- ❌ Do NOT bulk-collect Threads rows — they add titles/URLs only, no metrics

The supplemental tier exists to surface qualitative evidence:  
"Here is what people are saying about Claude on TikTok and Reddit."  
It is not used to claim statistical patterns.

---

## 6. Ethical & Legal Compliance

- All data is from public pages or public APIs
- No authenticated scraping, no login-wall bypassing
- No private API access
- Rate limits are respected (delays between requests, staying within API quotas)
- User-Agent strings identify the bot as a research tool
- No PII is stored (no email addresses, no DMs, no private data)
- Data is used solely for academic/competition purposes (HackNU 2026)
