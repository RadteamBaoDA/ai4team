import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.document_converter import DocumentConverter


class DocumentConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir()

        self.logger_patcher = mock.patch("src.document_converter.setup_logger", return_value=mock.Mock())
        self.mock_logger = self.logger_patcher.start()

        self.scanner_patcher = mock.patch("src.document_converter.FileScanner")
        self.mock_scanner_cls = self.scanner_patcher.start()
        self.mock_scanner = self.mock_scanner_cls.return_value
        # Provide a deterministic default path while allowing per-test overrides.
        self.mock_scanner.get_output_path.side_effect = (
            lambda input_file, *_: self.output_dir / f"{input_file.stem}.pdf"
        )

        self.factory_patcher = mock.patch("src.document_converter.ConverterFactory")
        self.mock_factory_cls = self.factory_patcher.start()
        self.mock_factory = self.mock_factory_cls.return_value

        self.converter = DocumentConverter(
            input_dir=str(self.input_dir),
            output_dir=str(self.output_dir),
            enable_progress_bar=False,
        )

    def tearDown(self):
        self.logger_patcher.stop()
        self.scanner_patcher.stop()
        self.factory_patcher.stop()
        self.temp_dir.cleanup()

    def test_find_all_documents_uses_scanner(self):
        expected = [self.input_dir / "doc.docx"]
        self.mock_scanner.find_all_documents.return_value = expected
        result = self.converter.find_all_documents()
        self.assertEqual(result, expected)
        self.mock_scanner.find_all_documents.assert_called_once()

    def test_get_output_path_delegates_to_scanner(self):
        target = self.output_dir / "custom.pdf"
        self.mock_scanner.get_output_path.side_effect = None
        self.mock_scanner.get_output_path.return_value = target
        doc = self.input_dir / "file.docx"
        path = self.converter.get_output_path(doc)
        self.assertEqual(path, target)
        self.mock_scanner.get_output_path.assert_called_once_with(doc, self.converter.input_dir, self.converter.output_dir)

    def test_convert_file_skips_when_up_to_date(self):
        doc = self.input_dir / "skip.docx"
        doc.write_text("content")
        self.mock_scanner.get_output_path.side_effect = None
        self.mock_scanner.get_output_path.return_value = self.output_dir / "skip.pdf"

        with mock.patch("src.document_converter.should_skip_conversion", return_value=True):
            success, output = self.converter.convert_file(doc)

        self.assertTrue(success)
        self.assertEqual(output, self.output_dir / "skip.pdf")
        self.mock_factory.get_converters_for_file.assert_not_called()

    def test_convert_file_uses_first_successful_converter(self):
        doc = self.input_dir / "convert.docx"
        doc.write_text("data")
        mock_converter = mock.Mock()
        mock_converter.convert.return_value = True
        self.mock_factory.get_converters_for_file.return_value = [mock_converter]

        with mock.patch("src.document_converter.should_skip_conversion", return_value=False):
            success, output = self.converter.convert_file(doc)

        self.assertTrue(success)
        self.assertEqual(output, self.output_dir / "convert.pdf")
        mock_converter.convert.assert_called_once_with(doc, output)

    def test_convert_file_failure_when_all_converters_fail(self):
        doc = self.input_dir / "bad.docx"
        doc.write_text("data")
        failing_converter = mock.Mock()
        failing_converter.convert.return_value = False
        self.mock_factory.get_converters_for_file.return_value = [failing_converter]

        with mock.patch("src.document_converter.should_skip_conversion", return_value=False):
            success, _ = self.converter.convert_file(doc, retry_count=0)

        self.assertFalse(success)

    def test_copy_file_skips_when_identical(self):
        doc = self.input_dir / "copy.txt"
        doc.write_text("data")
        with mock.patch("src.document_converter.should_skip_copy", return_value=True):
            success, _ = self.converter.copy_file(doc)
        self.assertTrue(success)

    def test_copy_file_copies_when_needed(self):
        doc = self.input_dir / "copy2.txt"
        doc.write_text("data")
        target = self.output_dir / "copy2.txt"
        self.mock_scanner.get_output_path.side_effect = None
        self.mock_scanner.get_output_path.return_value = target.with_suffix(".pdf")

        with mock.patch("src.document_converter.should_skip_copy", return_value=False), \
             mock.patch("shutil.copy2") as copy_mock:
            copy_mock.return_value = None
            success, output = self.converter.copy_file(doc)

        self.assertTrue(success)
        self.assertEqual(output, target)
        copy_mock.assert_called_once_with(doc, target)

    def test_categorize_by_size_groups_files(self):
        files = [Path("small"), Path("medium"), Path("large")]
        sizes = [50_000, 2_000_000, 20_000_000]
        with mock.patch.object(self.converter, "_get_file_size", side_effect=sizes):
            buckets = self.converter._categorize_by_size(files)
        self.assertEqual(buckets['small'], [files[0]])
        self.assertEqual(buckets['medium'], [files[1]])
        self.assertEqual(buckets['large'], [files[2]])

    def test_calculate_adaptive_workers_for_large_and_small(self):
        files = [Path("f1"), Path("f2"), Path("f3"), Path("f4"), Path("f5"), Path("f6")]  # six files
        with mock.patch.object(
            self.converter,
            "_categorize_by_size",
            return_value={'small': [], 'medium': [files[0]], 'large': files[1:]},
        ):
            self.converter.max_workers = 4
            workers = self.converter._calculate_adaptive_workers(files)
        self.assertEqual(workers, 2)

        with mock.patch.object(
            self.converter,
            "_categorize_by_size",
            return_value={'small': files, 'medium': [], 'large': []},
        ), mock.patch("os.cpu_count", return_value=8):
            self.converter.max_workers = 2
            workers = self.converter._calculate_adaptive_workers(files)
        self.assertEqual(workers, 4)

    def test_sort_by_priority_orders_by_size(self):
        convert_files = [Path("a"), Path("b")]
        copy_files = [Path("c")]
        with mock.patch.object(
            self.converter,
            "_get_file_size",
            side_effect=[100, 300, 200],
        ):
            ordered = self.converter._sort_by_priority(convert_files, copy_files)
        self.assertEqual(ordered, [(Path("b"), 'convert'), (Path("c"), 'copy'), (Path("a"), 'convert')])

    def test_convert_all_returns_zero_when_no_files(self):
        self.mock_scanner.categorize_files.return_value = ([], [])
        stats = self.converter.convert_all(enable_parallel=False)
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['failed'], 0)

    def test_convert_all_sequential_updates_stats(self):
        files_to_convert = [self.input_dir / "c1.docx"]
        files_to_copy = [self.input_dir / "c2.txt"]
        self.mock_scanner.categorize_files.return_value = (files_to_convert, files_to_copy)
        self.converter.enable_parallel = False

        with mock.patch.object(self.converter, "convert_file", return_value=(True, Path("out.pdf"))) as convert_mock, \
             mock.patch.object(self.converter, "copy_file", return_value=(False, Path("copy.txt"))) as copy_mock:
            stats = self.converter.convert_all()

        convert_mock.assert_called_once_with(files_to_convert[0])
        copy_mock.assert_called_once_with(files_to_copy[0])
        self.assertEqual(stats['converted'], 1)
        self.assertEqual(stats['copied'], 0)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['failed_files'], [str(files_to_copy[0])])

    def test_convert_all_parallel_path_invokes_parallel_helper(self):
        files_to_convert = [self.input_dir / "a.docx"]
        files_to_copy = [self.input_dir / "b.txt"]
        self.mock_scanner.categorize_files.return_value = (files_to_convert, files_to_copy)
        self.converter.enable_parallel = True

        with mock.patch.object(self.converter, "_convert_all_parallel") as parallel_mock, \
             mock.patch.object(self.converter, "_calculate_adaptive_workers", return_value=2):
            self.converter.convert_all()

        parallel_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
