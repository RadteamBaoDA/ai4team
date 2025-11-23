import unittest
from pathlib import Path
from unittest import mock

from src.converters.factory import ConverterFactory


class ConverterFactoryTests(unittest.TestCase):
    def test_get_converters_for_docx_respects_priority(self):
        with mock.patch("src.converters.factory.LibreOfficeConverter") as libre_mock, \
             mock.patch("src.converters.factory.MSOfficeConverter") as ms_mock, \
             mock.patch("src.converters.factory.DocxConverter") as docx_mock:
            libre_inst = libre_mock.return_value
            ms_inst = ms_mock.return_value
            docx_inst = docx_mock.return_value
            libre_inst.is_available.return_value = True
            ms_inst.is_available.return_value = False

            factory = ConverterFactory()
            converters = factory.get_converters_for_file(Path("file.docx"))

            self.assertIn(libre_inst, converters)
            self.assertNotIn(ms_inst, converters)
            self.assertEqual(converters[-1], docx_inst)

    def test_get_available_converters_info(self):
        factory = ConverterFactory()
        info = factory.get_available_converters_info()
        self.assertIn("LibreOffice", info)
        self.assertIn("Microsoft Office", info)
        self.assertTrue(info["Python Libraries"])


if __name__ == "__main__":
    unittest.main()
