import pytest

from drivegrab.links import file_id, folder_id

FID = "1F_OM4ns_HuZpYkqeeOxx0nWQXAfFR99e"
DIR = "1n64NVPNoKQdQDed63JWlLFKR3dE15M2f"


@pytest.mark.parametrize("url", [
    f"https://drive.google.com/file/d/{FID}/view?usp=drive_link",
    f"https://drive.google.com/file/d/{FID}/view",
    f"https://drive.google.com/file/d/{FID}",
    f"https://drive.google.com/open?id={FID}",
    f"https://drive.google.com/uc?export=download&id={FID}",
    f"https://docs.google.com/document/d/{FID}/edit",
])
def test_file_links(url):
    assert file_id(url) == FID
    assert folder_id(url) is None


@pytest.mark.parametrize("url", [
    f"https://drive.google.com/drive/folders/{DIR}?usp=sharing",
    f"https://drive.google.com/drive/folders/{DIR}",
    f"https://drive.google.com/drive/u/0/folders/{DIR}",
])
def test_folder_links(url):
    assert folder_id(url) == DIR
    assert file_id(url) is None


@pytest.mark.parametrize("url", ["", None, "https://example.com", "https://drive.google.com/drive/my-drive"])
def test_garbage(url):
    assert file_id(url) is None
    assert folder_id(url) is None
