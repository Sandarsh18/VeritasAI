import unittest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone
from backend.retrieval import search_newsapi

class TestTemporalFilter(unittest.TestCase):
    @patch('requests.get')
    def test_filter_old_articles(self, mock_get):
        """
        Tests that old articles are filtered out.
        """
        print("--- Testing Temporal Filter ---")
        
        # Mock response from NewsAPI
        mock_response = Mock()
        mock_response.status_code = 200
        
        old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        new_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        
        mock_response.json.return_value = {
            "articles": [
                {
                    "title": "Old Article",
                    "url": "http://example.com/old",
                    "publishedAt": old_date,
                },
                {
                    "title": "New Article",
                    "url": "http://example.com/new",
                    "publishedAt": new_date,
                },
                {
                    "title": "No Date Article",
                    "url": "http://example.com/no-date",
                    "publishedAt": None,
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the function with default 90 days filter
        results = search_newsapi("test query")
        
        print(f"Results: {results}")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], "New Article")
        self.assertEqual(results[1]['title'], "No Date Article")
        
        # Call the function with a 300 days filter
        results_300 = search_newsapi("test query", published_after_days=300)
        
        print(f"Results (300 days): {results_300}")
        
        self.assertEqual(len(results_300), 3)
        
        print("--- Temporal Filter test passed! ---")

if __name__ == "__main__":
    unittest.main()
