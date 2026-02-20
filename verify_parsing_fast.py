import sys
import unittest
from unittest.mock import patch, MagicMock

# Import the parser
from question_paper import QuestionPaperParser

# Read the debug text
with open(r"c:\Users\hp\answersheet_eval\debug_qp_text.txt", "r", encoding="utf-8") as f:
    OCR_TEXT = f.read()

class TestQPParsing(unittest.TestCase):
    @patch('question_paper.extract_text_from_file')
    def test_parsing_logic(self, mock_extract):
        mock_extract.return_value = OCR_TEXT
        
        parser = QuestionPaperParser()
        # Pass any dummy path since we mock the extractor
        schema = parser.parse_question_paper("dummy.pdf")
        
        print("\nParsed Schema Keys:", sorted(schema.keys(), key=lambda x: (len(x), x)))
        
        # Assertions
        self.assertIn("1", schema)
        self.assertIn("11", schema)
        self.assertIn("2", schema)
        
        # Check specific details for Q11
        if "11" in schema:
            print("Q11 detected correctly:", schema["11"])
            self.assertEqual(schema["11"]["max_marks"], 5)
            
        # Check if 10784 is GONE
        self.assertNotIn("10784", schema)

if __name__ == '__main__':
    unittest.main()
