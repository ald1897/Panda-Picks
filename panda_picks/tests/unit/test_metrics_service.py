import unittest
import pandas as pd
from panda_picks.analysis.services.metrics_service import compute_model_accuracy

class TestMetricsService(unittest.TestCase):
    def test_compute_model_accuracy_basic(self):
        picks = pd.DataFrame([
            {"WEEK":"WEEK1","Home_Team":"A","Away_Team":"B","Game_Pick":"A"},
            {"WEEK":"WEEK1","Home_Team":"C","Away_Team":"D","Game_Pick":"C"},
            {"WEEK":"WEEK2","Home_Team":"E","Away_Team":"F","Game_Pick":"F"},
        ])
        results = pd.DataFrame([
            {"WEEK":"WEEK1","Home_Team":"A","Away_Team":"B","Winner":"A"},  # correct
            {"WEEK":"WEEK1","Home_Team":"C","Away_Team":"D","Winner":"D"},  # incorrect
            {"WEEK":"WEEK2","Home_Team":"E","Away_Team":"F","Winner":"F"},  # correct
        ])
        overall, weekly = compute_model_accuracy(picks, results)
        self.assertEqual(overall, 2/3)
        wk1_acc = weekly[weekly['Week']=="WEEK1"]["Accuracy"].iloc[0]
        wk2_acc = weekly[weekly['Week']=="WEEK2"]["Accuracy"].iloc[0]
        self.assertEqual(wk1_acc, 0.5)
        self.assertEqual(wk2_acc, 1.0)

    def test_compute_model_accuracy_empty(self):
        picks = pd.DataFrame(columns=["WEEK","Home_Team","Away_Team","Game_Pick"])
        results = pd.DataFrame(columns=["WEEK","Home_Team","Away_Team","Winner"])
        overall, weekly = compute_model_accuracy(picks, results)
        self.assertIsNone(overall)
        self.assertTrue(weekly.empty)

if __name__ == '__main__':
    unittest.main()
