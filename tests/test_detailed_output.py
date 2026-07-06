import unittest

from structured_output import (
    DetectionOutput,
    OperationResult,
    Prediction,
    RetouchingLevel,
    RetouchingType,
    SuspiciousRegion,
    load_json_schema,
)


def operation_results():
    return {
        RetouchingType.EYE_ENLARGING: OperationResult(RetouchingLevel.SLIGHT, 0.91),
        RetouchingType.FACE_LIFTING: OperationResult(RetouchingLevel.OFF, 0.88),
        RetouchingType.SKIN_SMOOTHING: OperationResult(RetouchingLevel.MEDIUM, 0.87),
        RetouchingType.FACE_WHITENING: OperationResult(RetouchingLevel.OFF, 0.95),
    }


class DetailedOutputTests(unittest.TestCase):
    def make_output(self):
        return DetectionOutput(
            prediction=Prediction.FILTER_PROCESSED,
            confidence=0.94,
            retouching=operation_results(),
            suspicious_regions=[SuspiciousRegion("eye_area", 0.91)],
            explanation="Eye enlargement and medium skin smoothing detected.",
        )

    def test_round_trip(self):
        output = self.make_output()
        self.assertEqual(DetectionOutput.from_json(output.to_json()), output)
        self.assertEqual(output.artifact_types, ["eye_enlarging", "skin_smoothing"])

    def test_requires_all_operations(self):
        operations = operation_results()
        del operations[RetouchingType.FACE_LIFTING]
        with self.assertRaisesRegex(ValueError, "missing: face_lifting"):
            DetectionOutput(
                prediction="filter_processed",
                confidence=0.8,
                retouching=operations,
                suspicious_regions=[],
                explanation="A filter was detected.",
            )

    def test_schema_is_detailed(self):
        schema = load_json_schema()
        self.assertIn("retouching", schema["required"])
        self.assertIn("explanation", schema["required"])


if __name__ == "__main__":
    unittest.main()
