import unittest

from a7.review_results import review_output


class ReviewOutputTests(unittest.TestCase):
    def test_exact_classification_earns_full_score(self):
        review = review_output("classification-01", "SHOPPING")
        self.assertEqual(review["self_evaluation_score_1_to_10"], 10)

    def test_wrong_classification_is_scored_conservatively(self):
        review = review_output("classification-01", "CHORE")
        self.assertLess(review["self_evaluation_score_1_to_10"], 6)

    def test_correct_label_with_explanation_gets_accuracy_but_loses_adherence(self):
        review = review_output("priority-02", "LOW\nThis can wait until free time.")
        self.assertEqual(review["task_accuracy_0_to_3"], 3)
        self.assertEqual(review["instruction_adherence_0_to_2"], 1)
        self.assertLess(review["self_evaluation_score_1_to_10"], 10)

    def test_valid_extraction_checks_all_concerns(self):
        output = '''{"tasks":[
          {"title":"Clean kitchen","task_type":"CHORE","priority":"HIGH","description":"Clean before guests arrive"},
          {"title":"Buy snacks","task_type":"SHOPPING","priority":"HIGH","description":"Buy snacks for guests"},
          {"title":"Fix bathroom tap","task_type":"MAINTENANCE","priority":"URGENT","description":"Repair the leaking tap"}
        ]}'''
        review = review_output("extraction-01", output)
        self.assertEqual(review["self_evaluation_score_1_to_10"], 10)

    def test_repetitive_unstructured_output_scores_low(self):
        review = review_output("summary-01", "No, no, no, no, no, no")
        self.assertEqual(review["self_evaluation_score_1_to_10"], 1)


if __name__ == "__main__":
    unittest.main()
