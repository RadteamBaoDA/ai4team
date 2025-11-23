import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from src.converters.python_converters import (
    CsvConverter,
    DocxConverter,
    PptxConverter,
    XlsxConverter,
)


class PythonConvertersTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_docx_converter_success(self):
        fake_module = types.ModuleType("docx2pdf")
        called = {}

        def fake_convert(src, dst):
            called["args"] = (src, dst)

        fake_module.convert = fake_convert
        with mock.patch.dict(sys.modules, {"docx2pdf": fake_module}):
            input_file = self.temp_path / "a.docx"
            output_file = self.temp_path / "a.pdf"
            input_file.write_text("doc")
            converter = DocxConverter()
            self.assertTrue(converter.convert(input_file, output_file))
            self.assertEqual(called["args"], (str(input_file), str(output_file)))

    def _install_reportlab_stubs(self):
        reportlab = types.ModuleType("reportlab")
        reportlab.__path__ = []

        lib = types.ModuleType("reportlab.lib")
        lib.__path__ = []

        pagesizes = types.ModuleType("reportlab.lib.pagesizes")
        pagesizes.letter = (100, 200)
        pagesizes.landscape = lambda size: size

        colors = types.ModuleType("reportlab.lib.colors")
        colors.grey = "grey"
        colors.whitesmoke = "white"
        colors.beige = "beige"
        colors.black = "black"

        platypus = types.ModuleType("reportlab.platypus")

        class FakeDoc:
            def __init__(self, *args, **kwargs):
                self.built = False

            def build(self, elements):
                self.built = True
                self.elements = elements

        class FakeTable:
            def __init__(self, data):
                self.data = data
                self.styles = []

            def setStyle(self, style):
                self.styles.append(style)

        class FakeTableStyle:
            def __init__(self, styles):
                self.styles = styles

        class FakeParagraph:
            def __init__(self, text, style):
                self.text = text
                self.style = style

        class FakePageBreak:
            pass

        platypus.SimpleDocTemplate = FakeDoc
        platypus.Table = FakeTable
        platypus.TableStyle = FakeTableStyle
        platypus.PageBreak = FakePageBreak
        platypus.Paragraph = FakeParagraph

        styles = types.ModuleType("reportlab.lib.styles")

        class FakeStylesheet(dict):
            def __getitem__(self, key):
                return super().setdefault(key, object())

        styles.getSampleStyleSheet = lambda: FakeStylesheet()

        units = types.ModuleType("reportlab.lib.units")
        units.inch = 1

        pdfgen = types.ModuleType("reportlab.pdfgen")
        pdfgen.__path__ = []
        canvas_module = types.ModuleType("reportlab.pdfgen.canvas")

        class FakeCanvas:
            def __init__(self, *args, **kwargs):
                pass

            def setFont(self, *args, **kwargs):
                pass

            def drawString(self, *args, **kwargs):
                pass

            def showPage(self):
                pass

            def save(self):
                pass

        canvas_module.Canvas = FakeCanvas
        pdfgen.canvas = canvas_module

        modules = {
            "reportlab": reportlab,
            "reportlab.lib": lib,
            "reportlab.lib.pagesizes": pagesizes,
            "reportlab.lib.colors": colors,
            "reportlab.platypus": platypus,
            "reportlab.lib.styles": styles,
            "reportlab.lib.units": units,
            "reportlab.pdfgen": pdfgen,
            "reportlab.pdfgen.canvas": canvas_module,
        }
        return modules

    def test_xlsx_converter_success(self):
        fake_openpyxl = types.ModuleType("openpyxl")

        class FakeSheet:
            def __init__(self):
                self.rows = [["H1", "H2"], ["A", "B"]]

            def iter_rows(self, values_only=True):
                for row in self.rows:
                    yield row

        class FakeWorkbook:
            def __init__(self):
                self.sheetnames = ["Sheet1"]
                self._sheets = {"Sheet1": FakeSheet()}

            def __getitem__(self, item):
                return self._sheets[item]

        fake_openpyxl.load_workbook = lambda *args, **kwargs: FakeWorkbook()

        modules = {"openpyxl": fake_openpyxl}
        modules.update(self._install_reportlab_stubs())

        with mock.patch.dict(sys.modules, modules):
            converter = XlsxConverter()
            input_file = self.temp_path / "sheet.xlsx"
            output_file = self.temp_path / "sheet.pdf"
            input_file.write_text("sheet")
            self.assertTrue(converter.convert(input_file, output_file))

    def test_pptx_converter_success(self):
        fake_pptx = types.ModuleType("pptx")

        class FakeShape:
            def __init__(self, text):
                self.text = text

        class FakeSlide:
            def __init__(self):
                self.shapes = [FakeShape("Line1"), FakeShape("")]

        class FakePresentation:
            def __init__(self, *args, **kwargs):
                self.slides = [FakeSlide()]

        fake_pptx.Presentation = FakePresentation
        modules = {"pptx": fake_pptx}
        modules.update(self._install_reportlab_stubs())

        with mock.patch.dict(sys.modules, modules):
            converter = PptxConverter()
            input_file = self.temp_path / "slides.pptx"
            output_file = self.temp_path / "slides.pdf"
            input_file.write_text("slides")
            self.assertTrue(converter.convert(input_file, output_file))

    def test_csv_converter_success(self):
        modules = self._install_reportlab_stubs()
        with mock.patch.dict(sys.modules, modules):
            converter = CsvConverter()
            input_file = self.temp_path / "data.csv"
            output_file = self.temp_path / "data.pdf"
            input_file.write_text("col1,col2\n1,2\n")
            self.assertTrue(converter.convert(input_file, output_file))

    def test_converters_return_false_on_exception(self):
        with mock.patch.dict(sys.modules, {"docx2pdf": types.ModuleType("docx2pdf")}, clear=False):
            converter = DocxConverter()
            result = converter.convert(self.temp_path / "missing.docx", self.temp_path / "out.pdf")
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
