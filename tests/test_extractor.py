"""Unit tests for function extractor."""

import unittest
from ast_refactor.transformers.extractor import FunctionExtractor


class TestFunctionExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = FunctionExtractor()

    def test_python_extract_with_inputs_and_outputs(self):
        code = (
            "def process_data(factor):\n"
            "    base = 10\n"
            "    # extracted part start\n"
            "    a = base * 2\n"
            "    b = a + factor\n"
            "    # extracted part end\n"
            "    return b * 3\n"
        )
        res = self.extractor.extract(
            code=code,
            file_path="sample.py",
            start_line=4,
            end_line=5,
            new_function_name="compute_step",
        )
        self.assertIsNone(res.error)
        self.assertTrue(res.has_changed)
        self.assertIn("base", res.input_parameters)
        self.assertIn("factor", res.input_parameters)
        self.assertIn("b", res.output_variables)
        self.assertIn("def compute_step(base, factor):", res.modified_code)
        self.assertIn("b = compute_step(base, factor)", res.modified_code)

    def test_python_extract_no_output(self):
        code = (
            "def run_job(msg):\n"
            "    prefix = 'INFO:'\n"
            "    print(prefix, msg)\n"
            "    return True\n"
        )
        res = self.extractor.extract(
            code=code,
            file_path="sample.py",
            start_line=3,
            end_line=3,
            new_function_name="log_message",
        )
        self.assertIsNone(res.error)
        self.assertTrue(res.has_changed)
        self.assertIn("def log_message(", res.modified_code)
        self.assertIn("log_message(", res.modified_code)

    def test_extract_invalid_lines(self):
        code = "a = 1\n"
        res = self.extractor.extract(
            code=code,
            file_path="sample.py",
            start_line=10,
            end_line=15,
            new_function_name="bad",
        )
        self.assertIsNotNone(res.error)


    def test_python_extract_inside_class_method(self):
        code = (
            "class Calculator:\n"
            "    def compute(self, x):\n"
            "        factor = 2\n"
            "        result = x * factor\n"
            "        return result\n"
        )
        res = self.extractor.extract(
            code=code,
            file_path="calc.py",
            start_line=3,
            end_line=4,
            new_function_name="helper_calc",
        )
        self.assertIsNone(res.error)
        self.assertTrue(res.has_changed)
        self.assertIn("def helper_calc(x):", res.modified_code)
        self.assertIn("result = helper_calc(x)", res.modified_code)


if __name__ == "__main__":
    unittest.main()
