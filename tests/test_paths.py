from drivegrab.paths import as_pdf, safe_name, unique_path


def test_strips_drive_suffix():
    assert safe_name("Chapter_3_Slides.pdf - Google Drive") == "Chapter_3_Slides.pdf"
    assert safe_name("Лекция 1 - Google Диск") == "Лекция 1"


def test_replaces_bad_chars():
    assert safe_name('a/b:c*d?"e<f>g|h') == "a_b_c_d__e_f_g_h"


def test_fallback():
    assert safe_name("") == "untitled"
    assert safe_name(None, "x") == "x"
    assert safe_name(" . ") == "untitled"


def test_keeps_unicode():
    assert safe_name("Bütünleme 2025") == "Bütünleme 2025"


def test_as_pdf():
    assert as_pdf("notes") == "notes.pdf"
    assert as_pdf("notes.PDF") == "notes.PDF"


def test_unique_path(tmp_path):
    assert unique_path(tmp_path, "a.pdf") == tmp_path / "a.pdf"
    (tmp_path / "a.pdf").touch()
    assert unique_path(tmp_path, "a.pdf") == tmp_path / "a (1).pdf"
    (tmp_path / "a (1).pdf").touch()
    assert unique_path(tmp_path, "a.pdf") == tmp_path / "a (2).pdf"
