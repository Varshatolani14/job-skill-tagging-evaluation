import json
import unittest
from pathlib import Path

from evaluate_tags import (
    canonicalize,
    classify_tags,
    main,
    mentioned_skills,
    read_csv,
    skill_patterns,
)


class MentionedSkillsTests(unittest.TestCase):
    def setUp(self):
        self.skills = [
            "Machine Learning",
            "Microsoft Excel",
            "Node.js",
            "Research",
            "Social Media Marketing",
            "User Research",
        ]
        self.patterns = skill_patterns(self.skills)

    def test_title_only_mention_is_not_a_skill_requirement(self):
        required, optional = mentioned_skills(
            "Acme needs a Machine Learning Intern. Bonus if you know Machine Learning.",
            "Machine Learning Intern",
            self.patterns,
        )
        self.assertEqual(required, set())
        self.assertEqual(optional, {"Machine Learning"})

    def test_optional_skills_and_aliases_are_handled(self):
        required, optional = mentioned_skills(
            "Use Node.js and Microsoft Excel every day. "
            "Nice to have: Social Media Marketing.",
            "Developer Intern",
            self.patterns,
        )
        self.assertEqual(required, {"Node.js", "Microsoft Excel"})
        self.assertEqual(optional, {"Social Media Marketing"})

    def test_user_research_does_not_create_a_research_mention(self):
        required, optional = mentioned_skills(
            "You will use User Research and Figma.", "", self.patterns
        )
        self.assertEqual(required, {"User Research"})
        self.assertEqual(optional, set())

    def test_broader_social_media_term_is_not_the_listed_marketing_skill(self):
        required, optional = mentioned_skills(
            "You will manage Social Media.", "", self.patterns
        )
        self.assertEqual(required, set())
        self.assertEqual(optional, set())

    def test_tag_alias_maps_to_the_listed_skill(self):
        skill_map = {skill.casefold(): skill for skill in self.skills}
        self.assertEqual(canonicalize("Excel", skill_map), "Microsoft Excel")

    def test_duplicate_aliases_do_not_inflate_correct_tag_count(self):
        skill_map = {skill.casefold(): skill for skill in self.skills}
        right_required, right_optional, wrong, predicted = classify_tags(
            ["Microsoft Excel", "Excel"],
            {"Microsoft Excel"},
            set(),
            skill_map,
        )
        self.assertEqual(right_required, {"Microsoft Excel"})
        self.assertEqual(right_optional, set())
        self.assertEqual(wrong, ["Excel"])
        self.assertEqual(predicted, {"Microsoft Excel"})


class DatasetAuditTests(unittest.TestCase):
    def test_outputs_reconcile_to_all_50_source_rows(self):
        root = Path(__file__).resolve().parent
        main()
        jobs = read_csv(root / "job-descriptions-tagged.csv")
        labels = read_csv(root / "labels.csv")
        metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))

        self.assertEqual(len(jobs), 50)
        self.assertEqual(len(labels), 50)
        self.assertEqual(
            [job["jd_id"] for job in jobs], [row["jd_id"] for row in labels]
        )
        self.assertEqual(metrics["model_tag_count"], 200)
        self.assertEqual(metrics["right_tag_count"], 170)
        self.assertEqual(metrics["wrong_tag_count"], 30)
        self.assertEqual(metrics["required_skill_count"], 177)
        self.assertEqual(metrics["missed_required_count"], 27)
        for row in labels:
            self.assertEqual(
                int(row["tag_count"]),
                int(row["right_tag_count"]) + int(row["wrong_tag_count"]),
                row["jd_id"],
            )


if __name__ == "__main__":
    unittest.main()
