#!/usr/bin/env python3
"""Evaluate the provided job-skill tags against the supplied skill inventory."""

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parent
JOBS_FILE = ROOT / "job-descriptions-tagged.csv"
SKILLS_FILE = ROOT / "skill-list.csv"
LABELS_FILE = ROOT / "labels.csv"
METRICS_FILE = ROOT / "metrics.json"

ALIASES = {
    "financial modeling": "Financial Modelling",
    "node": "Node.js",
    "postgres": "PostgreSQL",
    "excel": "Microsoft Excel",
    "js": "JavaScript",
    "ml": "Machine Learning",
}
OPTIONAL_CUE = re.compile(
    r"\b(?:bonus|nice to have|plus|optional|not a must)\b", re.IGNORECASE
)


def read_csv(path: Path) -> List[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def canonicalize(value: str, skill_by_normalized: Dict[str, str]) -> Optional[str]:
    key = normalized(value)
    if key in skill_by_normalized:
        return skill_by_normalized[key]
    alias_target = ALIASES.get(key)
    if alias_target:
        target_key = normalized(alias_target)
        if target_key in skill_by_normalized:
            return skill_by_normalized[target_key]
    return None


def skill_patterns(skills: List[str]) -> List[Tuple[str, re.Pattern]]:
    patterns = []
    for skill in skills:
        variants = [skill]
        variants.extend(
            alias for alias, target in ALIASES.items()
            if normalized(target) == normalized(skill)
        )
        for variant in variants:
            pattern = re.compile(
                r"(?<!\w)" + re.escape(variant) + r"(?!\w)", re.IGNORECASE
            )
            patterns.append((skill, pattern))
    return patterns


def mentioned_skills(
    description: str,
    title: str,
    patterns: List[Tuple[str, re.Pattern]],
) -> Tuple[Set[str], Set[str]]:
    required: Set[str] = set()
    optional: Set[str] = set()
    if title.strip():
        description = re.sub(
            re.escape(title.strip()), " ", description, count=1, flags=re.IGNORECASE
        )
    # Splitting on sentence-ending punctuation keeps the optional cue local to
    # the skill it qualifies (for example, "X is a plus, not a must.").
    sentences = re.split(r"(?<=[.!?])\s+", description)
    for sentence in sentences:
        is_optional = OPTIONAL_CUE.search(sentence) is not None
        matches = []
        for canonical, pattern in patterns:
            matches.extend(
                (match.start(), match.end(), canonical)
                for match in pattern.finditer(sentence)
            )
        occupied = []
        for start, end, canonical in sorted(
            matches, key=lambda match: match[1] - match[0], reverse=True
        ):
            if any(
                start < used_end and end > used_start
                for used_start, used_end in occupied
            ):
                continue
            occupied.append((start, end))
            (optional if is_optional else required).add(canonical)
    optional.difference_update(required)
    return required, optional


def classify_tags(
    tags: List[str],
    required: Set[str],
    optional: Set[str],
    skill_by_normalized: Dict[str, str],
) -> Tuple[Set[str], Set[str], List[str], Set[str]]:
    right_required: Set[str] = set()
    right_optional: Set[str] = set()
    wrong: List[str] = []
    predicted: Set[str] = set()

    for tag in tags:
        canonical = canonicalize(tag, skill_by_normalized)
        if canonical is None or canonical in predicted:
            wrong.append(tag)
            continue
        predicted.add(canonical)
        if canonical in required:
            right_required.add(canonical)
        elif canonical in optional:
            right_optional.add(canonical)
        else:
            wrong.append(tag)

    return right_required, right_optional, wrong, predicted


def main():
    jobs = read_csv(JOBS_FILE)
    skill_rows = read_csv(SKILLS_FILE)
    if not skill_rows or "skill" not in skill_rows[0]:
        raise ValueError("skill-list.csv must have a 'skill' column")
    if not jobs or not {"jd_id", "description", "model_tags"}.issubset(jobs[0]):
        raise ValueError(
            "job-descriptions-tagged.csv must have jd_id, description, "
            "and model_tags columns"
        )

    skills = [row["skill"].strip() for row in skill_rows]
    skill_by_normalized = {normalized(skill): skill for skill in skills}
    if len(skill_by_normalized) != len(skills):
        raise ValueError("skill-list.csv contains duplicate skill names")
    patterns = skill_patterns(skills)

    ids = [row["jd_id"].strip() for row in jobs]
    if len(set(ids)) != len(ids):
        raise ValueError("job-descriptions-tagged.csv contains duplicate jd_id values")

    labels = []
    totals = Counter()
    for job in jobs:
        required, optional = mentioned_skills(
            job["description"], job.get("title", ""), patterns
        )
        tags = [tag.strip() for tag in job["model_tags"].split(";") if tag.strip()]
        right_required, right_optional, wrong, predicted_canonical = classify_tags(
            tags, required, optional, skill_by_normalized
        )

        missing = required - predicted_canonical
        row = {
            "jd_id": job["jd_id"],
            "required_skills": sorted(required),
            "optional_skills": sorted(optional),
            "right_required_tags": sorted(right_required),
            "right_optional_tags": sorted(right_optional),
            "wrong_tags": wrong,
            "missing_required_skills": sorted(missing),
            "tag_count": len(tags),
            "right_tag_count": len(right_required) + len(right_optional),
            "wrong_tag_count": len(wrong),
            "required_skill_count": len(required),
            "missed_required_count": len(missing),
        }
        labels.append(row)
        totals.update(
            tag_count=len(tags),
            right_tag_count=row["right_tag_count"],
            right_required_tag_count=len(right_required),
            right_optional_tag_count=len(right_optional),
            wrong_tag_count=len(wrong),
            required_skill_count=len(required),
            missed_required_count=len(missing),
            optional_skill_count=len(optional),
        )

    with LABELS_FILE.open("w", encoding="utf-8", newline="") as stream:
        fieldnames = [
            "jd_id",
            "required_skills",
            "optional_skills",
            "right_required_tags",
            "right_optional_tags",
            "wrong_tags",
            "missing_required_skills",
            "tag_count",
            "right_tag_count",
            "wrong_tag_count",
            "required_skill_count",
            "missed_required_count",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in labels:
            writer.writerow(
                {
                    key: "; ".join(value) if isinstance(value, list) else value
                    for key, value in row.items()
                }
            )

    metrics = {
        "job_count": len(jobs),
        "model_tag_count": totals["tag_count"],
        "right_tag_count": totals["right_tag_count"],
        "right_required_tag_count": totals["right_required_tag_count"],
        "right_optional_tag_count": totals["right_optional_tag_count"],
        "wrong_tag_count": totals["wrong_tag_count"],
        "tag_right_rate_percent": (
            round(100 * totals["right_tag_count"] / totals["tag_count"], 2)
            if totals["tag_count"]
            else 0
        ),
        "required_skill_count": totals["required_skill_count"],
        "required_skill_hit_count": (
            totals["required_skill_count"] - totals["missed_required_count"]
        ),
        "missed_required_count": totals["missed_required_count"],
        "required_skill_miss_rate_percent": (
            round(
                100 * totals["missed_required_count"] / totals["required_skill_count"],
                2,
            )
            if totals["required_skill_count"]
            else 0
        ),
        "required_skill_coverage_percent": (
            round(
                100
                * (
                    totals["required_skill_count"]
                    - totals["missed_required_count"]
                )
                / totals["required_skill_count"],
                2,
            )
            if totals["required_skill_count"]
            else 0
        ),
        "optional_skill_count": totals["optional_skill_count"],
    }
    METRICS_FILE.write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
