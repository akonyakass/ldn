import pandas as pd, re

df = pd.read_csv("data/final/dataset.csv")
df["pub"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
text = (df["title"].fillna("") + " " + df["text_snippet"].fillna("")).str.lower()

releases = {
    "Claude 3.5 Sonnet": [r"claude\s+3\.5\s+sonnet", r"claude-3-5"],
    "Claude 3.7 Sonnet": [r"claude\s+3\.7", r"claude-3-7", r"claude 3.7"],
    "Claude Opus 4.5": [r"opus\s+4\.5", r"claude\s+4\.5\b"],
    "Claude Opus 4.6": [r"opus\s+4\.6", r"claude\s+4\.6\b", r"80\.8"],
    "Claude Sonnet 4.x": [r"sonnet\s+4\.", r"claude\s+sonnet\s+4"],
    "Claude Code (IDE)": [
        r"claude\s+code\s+ide",
        r"claude\s+code\s+launch",
        r"claude\s+code\s+release",
    ],
}

print(f"{'Release':25s}  {'Posts':>6}  {'Date range'}")
print("-" * 60)
for name, patterns in releases.items():
    mask = text.apply(lambda t: any(re.search(p, t) for p in patterns))
    sub = df[mask]
    dated = sub["pub"].dropna()
    dmin = str(dated.min().date()) if len(dated) else "?"
    dmax = str(dated.max().date()) if len(dated) else "?"
    print(f"{name:25s}  {len(sub):6d}  {dmin} -> {dmax}")

# Also show monthly post volume to see natural spikes
print("\n--- Monthly post volume (all data with dates) ---")
df2 = df[df["pub"].notna()].copy()
df2["month"] = df2["pub"].dt.to_period("M")
print(df2["month"].value_counts().sort_index().to_string())
