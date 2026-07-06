import json
import unittest

from baseline_output import BaselineOutput, load_json_schema


class BaselineOutputTests(unittest.TestCase):
    def test_round_trip(self):
        output = BaselineOutput(is_retouched=True, confidence=0.94)
        restored = BaselineOutput.from_json(output.to_json())

        self.assertEqual(restored, output)
        self.assertEqual(
            json.loads(output.to_json()),
            {
                "schema_version": "1.0.0",
                "is_retouched": True,
                "confidence": 0.94,
            },
        )

    def test_supports_not_retouched_prediction(self):
        output = BaselineOutput(is_retouched=False, confidence=0.88)

        self.assertFalse(output.is_retouched)

    def test_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "boolean"):
            BaselineOutput(is_retouched=1, confidence=0.8)
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            BaselineOutput(is_retouched=True, confidence=1.1)

    def test_rejects_missing_and_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "missing: confidence"):
            BaselineOutput.from_dict(
                {"schema_version": "1.0.0", "is_retouched": True}
            )
        with self.assertRaisesRegex(ValueError, "unknown field.*explanation"):
            BaselineOutput.from_dict(
                {
                    "schema_version": "1.0.0",
                    "is_retouched": True,
                    "confidence": 0.8,
                    "explanation": "Retouched.",
                }
            )

    def test_schema_matches_baseline_contract(self):
        schema = load_json_schema()

        self.assertEqual(
            schema["required"],
            ["schema_version", "is_retouched", "confidence"],
        )
        self.assertEqual(schema["properties"]["is_retouched"]["type"], "boolean")


if __name__ == "__main__":
    unittest.main()
