import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from src.converters.libreoffice_converter import LibreOfficeConverter


class LibreOfficeConverterTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(LibreOfficeConverter, "_check_availability", lambda self: None)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.converter = LibreOfficeConverter()

    def test_is_available_false_until_command_set(self):
        self.assertFalse(self.converter.is_available())
        self.converter._command = "soffice"  # noqa: SLF001 (test-only access)
        self.assertTrue(self.converter.is_available())

    def test_convert_success_moves_generated_file(self):
        self.converter._command = "soffice"  # noqa: SLF001 (test-only access)
        tmpdir = Path(tempfile.mkdtemp())
        input_file = tmpdir / "source.docx"
        output_file = tmpdir / "out" / "final.pdf"
        input_file.write_text("doc")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        def fake_run(cmd, capture_output, timeout):
            outdir = Path(cmd[cmd.index("--outdir") + 1])
            generated = outdir / f"{input_file.stem}.pdf"
            generated.write_text("pdf")
            return types.SimpleNamespace(returncode=0)

        with mock.patch("src.converters.libreoffice_converter.subprocess.run", side_effect=fake_run):
            result = self.converter.convert(input_file, output_file)

        self.assertTrue(result)
        self.assertTrue(output_file.exists())

    def test_convert_failure_when_not_available(self):
        result = self.converter.convert(Path("missing.docx"), Path("out.pdf"))
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
