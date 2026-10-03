import unittest
from fastapi.testclient import TestClient
from main import app

class TestLLMvsRAGBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_status(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("api_key_configured", data)
        self.assertIn("documents_count", data)

    def test_sample_questions(self):
        response = self.client.get("/api/sample-questions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
        self.assertIn("question", data[0])

    def test_compare_endpoint(self):
        payload = {"question": "What is the qubit count of Nova-X Processor?"}
        response = self.client.post("/api/compare", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("plain_llm_answer", data)
        self.assertIn("rag_answer", data)
        self.assertIn("retrieved_docs", data)
        self.assertTrue(len(data["retrieved_docs"]) > 0)

    def test_evaluate_and_stats(self):
        eval_payload = {
            "comparison_id": "cmp_test123",
            "question": "What is the qubit count of Nova-X Processor?",
            "plain_llm_correct": False,
            "rag_correct": True
        }
        response = self.client.post("/api/evaluate", json=eval_payload)
        self.assertEqual(response.status_code, 200)
        stats = response.json()
        self.assertEqual(stats["total_evaluated"], 1)
        self.assertEqual(stats["rag_correct_count"], 1)
        self.assertEqual(stats["plain_llm_correct_count"], 0)
        self.assertEqual(stats["rag_accuracy_pct"], 100.0)

if __name__ == "__main__":
    unittest.main()
