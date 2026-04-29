from src.core import encoder


class _FakeTags:
    def __init__(self):
        self.frames = []

    def delall(self, _name):
        return None

    def add(self, frame):
        self.frames.append(frame)

    def save(self, _file_path, v2_version=3):
        self.saved_version = v2_version


def test_embed_mp3_metadata_adds_author_and_cover(monkeypatch, tmp_path):
    tags = _FakeTags()
    mp3_path = tmp_path / "chapter_01.mp3"
    cover_path = tmp_path / "cover.png"
    mp3_path.write_bytes(b"fake-mp3")
    cover_path.write_bytes(b"fake-cover")

    monkeypatch.setattr(encoder, "ID3", lambda _path: tags)
    monkeypatch.setattr(encoder, "TIT2", lambda **kwargs: ("TIT2", kwargs))
    monkeypatch.setattr(encoder, "TALB", lambda **kwargs: ("TALB", kwargs))
    monkeypatch.setattr(encoder, "TPE1", lambda **kwargs: ("TPE1", kwargs))
    monkeypatch.setattr(encoder, "TRCK", lambda **kwargs: ("TRCK", kwargs))
    monkeypatch.setattr(encoder, "APIC", lambda **kwargs: ("APIC", kwargs))

    encoder.embed_mp3_metadata(
        str(mp3_path),
        title="Chapter 1",
        album="Sample Book",
        artist="Jane PDF",
        track_number=1,
        total_tracks=3,
        cover_path=str(cover_path),
    )

    frame_names = [name for name, _kwargs in tags.frames]
    assert "TIT2" in frame_names
    assert "TALB" in frame_names
    assert "TPE1" in frame_names
    assert "TRCK" in frame_names
    assert "APIC" in frame_names