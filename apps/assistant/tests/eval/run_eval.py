"""Top-1 / top-3 accuracy per retriever on tests/eval/cases.yaml.

    python -m tests.eval.run_eval
"""

from pathlib import Path

import yaml

from app.retrieval import EmbeddingRetriever, HybridRetriever, KeywordRetriever

CASES = yaml.safe_load((Path(__file__).parent / "cases.yaml").read_text(encoding="utf-8"))


def retrievers():
    keyword, embedding = KeywordRetriever(), EmbeddingRetriever()
    return [keyword, embedding, HybridRetriever(keyword, embedding)]


def misses(retriever, kind: str, k: int = 1) -> list[str]:
    out = []
    for case in CASES[kind]:
        titles = [e.title.lower() for e, _ in retriever.search(case["text"], k)]
        if not any(case["want"].lower() in t for t in titles):
            out.append(case["text"])
    return out


def evaluate(retriever) -> dict[str, dict]:
    out = {}
    for kind in ("exact", "paraphrase"):
        n = len(CASES[kind])
        out[kind] = {
            "n": n,
            "top1": 1 - len(misses(retriever, kind, 1)) / n,
            "top3": 1 - len(misses(retriever, kind, 3)) / n,
        }
    negatives = CASES["negative"]
    rejected = sum(not retriever.search(c["text"], 3) for c in negatives)
    out["negative"] = {"n": len(negatives), "rejected": rejected / len(negatives)}
    return out


def table(results: dict[str, dict]) -> str:
    rows = [
        "| Retriever | Exact top-1 | Exact top-3 | Paraphrase top-1 | Paraphrase top-3 | Negatives rejected |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in results.items():
        e, p = r["exact"], r["paraphrase"]
        rows.append(
            f"| {name} | {e['top1']:.0%} | {e['top3']:.0%} | {p['top1']:.0%} | {p['top3']:.0%} "
            f"| {r['negative']['rejected']:.0%} |"
        )
    return "\n".join(rows)


if __name__ == "__main__":
    rs = retrievers()
    results = {r.name: evaluate(r) for r in rs}
    n = results["keyword"]
    print(f"cases: {n['exact']['n']} exact, {n['paraphrase']['n']} paraphrase, {n['negative']['n']} negative\n")
    print(table(results))
    for r in rs:
        for kind in ("exact", "paraphrase"):
            for text in misses(r, kind, 1):
                print(f"  {r.name} top-1 miss ({kind}): {text}")
