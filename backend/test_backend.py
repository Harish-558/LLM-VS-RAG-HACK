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

    def test_pdf_upload_and_compare(self):
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 78>>stream\n"
            b"BT /F1 12 Tf 100 700 Td (Solaris Falcon drone has an endurance of 74 hours.) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000056 00000 n \n0000000111 00000 n \n0000000234 00000 n \n0000000362 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n431\n%%EOF"
        )
        files = {"file": ("solaris_drone.pdf", pdf_bytes, "application/pdf")}
        upload_resp = self.client.post("/api/upload-pdf", files=files)
        self.assertEqual(upload_resp.status_code, 200)
        up_data = upload_resp.json()
        self.assertEqual(up_data["status"], "success")
        self.assertEqual(up_data["filename"], "solaris_drone.pdf")
        self.assertGreater(up_data["chunks_count"], 0)

        # Query about the uploaded PDF
        cmp_payload = {"question": "What is the endurance of Solaris Falcon drone?"}
        cmp_resp = self.client.post("/api/compare", json=cmp_payload)
        self.assertEqual(cmp_resp.status_code, 200)
        cmp_data = cmp_resp.json()
        self.assertTrue(len(cmp_data["retrieved_docs"]) > 0)
        self.assertIn("Solaris Falcon", cmp_data["retrieved_docs"][0]["content"])
        self.assertEqual(cmp_data["retrieved_docs"][0]["page"], 1)

        # Reset knowledge base
        reset_resp = self.client.post("/api/reset-knowledge-base")
        self.assertEqual(reset_resp.status_code, 200)
        status_data = reset_resp.json()
        self.assertEqual(status_data["status"], "online")
        self.assertIsNone(status_data["active_pdf"])

if __name__ == "__main__":
    unittest.main()
