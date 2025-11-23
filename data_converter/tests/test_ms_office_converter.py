import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.converters.ms_office_converter import (
    MSOfficeConverter,
    XL_FIND_DIRECTION_PREV,
)


class MSOfficeConverterTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(MSOfficeConverter, "_check_availability", lambda self: None)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.converter = MSOfficeConverter()
        self.converter._word_path = "word.exe"  # noqa: SLF001
        self.converter._excel_path = "excel.exe"  # noqa: SLF001
        self.converter._powerpoint_path = "ppt.exe"  # noqa: SLF001

    def test_convert_dispatches_to_word(self):
        temp_in = Path(tempfile.mkdtemp()) / "doc.docx"
        temp_out = temp_in.with_suffix(".pdf")
        temp_in.write_text("doc")

        with mock.patch.object(self.converter, "_convert_with_word", return_value=True) as mocked:
            self.assertTrue(self.converter.convert(temp_in, temp_out))
            mocked.assert_called_once()

    def test_convert_dispatches_to_excel(self):
        temp_in = Path(tempfile.mkdtemp()) / "sheet.xlsx"
        temp_out = temp_in.with_suffix(".pdf")
        temp_in.write_text("sheet")

        with mock.patch.object(self.converter, "_convert_with_excel", return_value=True) as mocked:
            self.assertTrue(self.converter.convert(temp_in, temp_out))
            mocked.assert_called_once()

    def test_convert_dispatches_to_powerpoint(self):
        temp_in = Path(tempfile.mkdtemp()) / "slides.pptx"
        temp_out = temp_in.with_suffix(".pdf")
        temp_in.write_text("slides")

        with mock.patch.object(self.converter, "_convert_with_powerpoint", return_value=True) as mocked:
            self.assertTrue(self.converter.convert(temp_in, temp_out))
            mocked.assert_called_once()

    def test_get_sheet_bounds(self):
        converter = self.converter

        class FakeCell:
            def __init__(self, row, column):
                self.Row = row
                self.Column = column

        class FakeCells:
            def Find(self, text, LookIn=None, SearchOrder=None, SearchDirection=None):  # noqa: N802
                if SearchDirection == XL_FIND_DIRECTION_PREV:
                    return FakeCell(10, 5)
                return FakeCell(2, 1)

        class FakeSheet:
            Cells = FakeCells()

        bounds = converter._get_sheet_bounds(FakeSheet())
        self.assertEqual(bounds, (2, 1, 10, 5))

        class ErrorCells:
            def Find(self, *args, **kwargs):  # noqa: N802
                raise RuntimeError("fail")

        class ErrorSheet:
            Cells = ErrorCells()

        self.assertIsNone(converter._get_sheet_bounds(ErrorSheet()))


if __name__ == "__main__":
    unittest.main()
