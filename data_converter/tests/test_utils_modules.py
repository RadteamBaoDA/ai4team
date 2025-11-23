import hashlib
import logging
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from src.utils import file_hash, file_scanner, hash_cache, logger as logger_utils


class FileHashTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        file_hash.calculate_file_hash.cache_clear()  # type: ignore[attr-defined]

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_file(self, name: str, data: bytes) -> Path:
        file_path = self.temp_path / name
        file_path.write_bytes(data)
        return file_path

    def test_calculate_file_hash_basic_md5(self):
        source = self._write_file("sample.bin", b"hello utils")
        expected = hashlib.md5(b"hello utils").hexdigest()

        actual = file_hash.calculate_file_hash(source, use_persistent_cache=False)

        self.assertEqual(actual, expected)

    def test_calculate_file_hash_uses_persistent_cache(self):
        source = self._write_file("cached.txt", b"persistent")
        stat = source.stat()

        class DummyCache:
            def __init__(self):
                self.store = {}

            def _key(self, file_path, file_size, modified_ns, algorithm):
                return (str(Path(file_path).resolve()), file_size, modified_ns, algorithm)

            def get(self, file_path, file_size, modified_ns, algorithm):
                return self.store.get(self._key(file_path, file_size, modified_ns, algorithm))

            def set(self, file_path, file_size, modified_ns, hash_value, algorithm):
                self.store[self._key(file_path, file_size, modified_ns, algorithm)] = hash_value

        dummy_cache = DummyCache()

        with mock.patch("src.utils.file_hash.get_hash_cache", return_value=dummy_cache):
            first = file_hash.calculate_file_hash(source)

        self.assertIn(
            (str(source.resolve()), stat.st_size, getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)), "md5"),
            dummy_cache.store,
        )

        with mock.patch("src.utils.file_hash.get_hash_cache", return_value=dummy_cache), \
             mock.patch("src.utils.file_hash._calculate_file_hash_cached", side_effect=RuntimeError("should not hash")):
            second = file_hash.calculate_file_hash(source)

        self.assertEqual(first, second)

    def test_calculate_file_hash_invalid_algorithm(self):
        source = self._write_file("algo.txt", b"data")
        result = file_hash._calculate_file_hash_cached(str(source), "nope", int(time.time_ns()), source.stat().st_size)
        self.assertEqual(result, "")

    def test_files_are_identical_variants(self):
        file_a = self._write_file("a.bin", b"abc")
        file_b = self._write_file("b.bin", b"xyz")
        self.assertFalse(file_hash.files_are_identical(file_a, file_b))

        file_c = self._write_file("c.bin", b"same")
        file_d = self._write_file("d.bin", b"same")
        self.assertTrue(file_hash.files_are_identical(file_c, file_d))

    def test_should_skip_helpers(self):
        src = self._write_file("input.txt", b"unchanged")
        dest = self.temp_path / "out.txt"
        dest.write_bytes(b"unchanged")
        self.assertTrue(file_hash.should_skip_copy(src, dest))
        self.assertTrue(file_hash.should_skip_conversion(src, dest))

        other = self._write_file("copy.txt", b"new data")
        self.assertFalse(file_hash.should_skip_copy(other, dest))

        converted_output = dest.with_suffix(".pdf")
        self.assertFalse(file_hash.should_skip_conversion(src, converted_output))


class FileScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name)
        (self.input_dir / "nested").mkdir()
        (self.input_dir / "docs").mkdir()

        (self.input_dir / "doc1.docx").write_text("doc")
        (self.input_dir / "docs" / "sheet.xlsx").write_text("sheet")
        (self.input_dir / "nested" / "readme.txt").write_text("readme")
        (self.input_dir / "skip.exe").write_text("skip")

        self.scanner = file_scanner.FileScanner(self.input_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_all_documents(self):
        documents = self.scanner.find_all_documents()
        names = {path.name for path in documents}
        self.assertIn("doc1.docx", names)
        self.assertIn("sheet.xlsx", names)
        self.assertIn("readme.txt", names)
        self.assertNotIn("skip.exe", names)

    def test_categorize_files(self):
        to_convert, to_copy = self.scanner.categorize_files()
        convert_names = {p.name for p in to_convert}
        copy_names = {p.name for p in to_copy}
        self.assertIn("doc1.docx", convert_names)
        self.assertIn("readme.txt", copy_names)

    def test_get_output_path_preserves_structure(self):
        output_dir = self.input_dir / "output"
        target = self.input_dir / "docs" / "report.docx"
        target.write_text("report")

        result = self.scanner.get_output_path(target, self.input_dir, output_dir)

        expected = output_dir / "docs" / "report_d.pdf"
        self.assertEqual(result, expected)
        self.assertTrue(result.parent.exists())


class HashCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "cache.db"
        self.cache = hash_cache.HashCache(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_set_and_get(self):
        file_path = Path("/tmp/sample.docx")
        self.cache.set(file_path, 10, 123, "abc")
        self.assertEqual(self.cache.get(file_path, 10, 123), "abc")

    def test_clear_old_entries(self):
        file_path = Path("/tmp/sample2.docx")
        self.cache.set(file_path, 5, 999, "hash")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE file_hashes SET cached_at = ?",
                ("2000-01-01T00:00:00",),
            )
            conn.commit()
        self.cache.clear_old_entries(days=1)
        self.assertIsNone(self.cache.get(file_path, 5, 999))

    def test_get_stats(self):
        self.cache.set(Path("/tmp/a.docx"), 1, 111, "a")
        stats = self.cache.get_stats()
        self.assertEqual(stats["total_entries"], 1)
        self.assertIsNotNone(stats["oldest_entry"])
        self.assertIsNotNone(stats["newest_entry"])

    def test_get_hash_cache_singleton(self):
        original = hash_cache._hash_cache
        hash_cache._hash_cache = None

        try:
            with mock.patch("src.utils.hash_cache.HashCache", return_value="dummy") as patched:
                first = hash_cache.get_hash_cache()
                second = hash_cache.get_hash_cache()
                self.assertEqual(first, "dummy")
                self.assertEqual(second, "dummy")
                patched.assert_called_once()
        finally:
            hash_cache._hash_cache = original


class LoggerTests(unittest.TestCase):
    def test_setup_logger_creates_handlers_once(self):
        logger_name = "test.utils.logger"
        logger = logger_utils.setup_logger(logger_name)

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        self.assertEqual(len(file_handlers), 1)
        self.assertEqual(len(stream_handlers), 1)

        file_handler = file_handlers[0]
        self.assertTrue(Path(file_handler.baseFilename).exists())

        logger_again = logger_utils.setup_logger(logger_name)
        self.assertIs(logger, logger_again)
        self.assertEqual(len(logger_again.handlers), len(logger.handlers))

        for handler in logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                log_path = Path(handler.baseFilename)
            handler.close()
            logger.removeHandler(handler)
            if isinstance(handler, logging.FileHandler) and log_path.exists():
                try:
                    log_path.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
