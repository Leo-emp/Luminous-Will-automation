
# ============================================================
# TEST BLOB STORAGE
# Tests for Vercel Blob upload + queue management
# Covers: token detection, upload gate, queue gate
#
# All tests run without a real token — they verify that each
# function correctly short-circuits when the token is absent.
# ============================================================


def test_blob_not_available_without_token(monkeypatch):
    # When BLOB_READ_WRITE_TOKEN is empty, is_blob_available must return False
    # so every downstream function can skip the upload path cleanly
    import config
    monkeypatch.setattr(config, "BLOB_READ_WRITE_TOKEN", "")
    from blob_storage import is_blob_available
    assert is_blob_available() is False


def test_blob_available_with_token(monkeypatch):
    # When a token is present, is_blob_available must return True
    # so the upload path is activated
    import config
    monkeypatch.setattr(config, "BLOB_READ_WRITE_TOKEN", "test_token")
    from blob_storage import is_blob_available
    assert is_blob_available() is True


def test_upload_returns_none_without_token(monkeypatch):
    # upload_file must silently return None when the token is missing
    # so the pipeline can continue without crashing
    import config
    monkeypatch.setattr(config, "BLOB_READ_WRITE_TOKEN", "")
    from blob_storage import upload_file
    result = upload_file("some_file.mp4")
    assert result is None


def test_add_to_queue_returns_none_without_token(monkeypatch):
    # add_to_queue must silently return None when the token is missing
    # so the pipeline DONE section still works (queue_entry will be None)
    import config
    monkeypatch.setattr(config, "BLOB_READ_WRITE_TOKEN", "")
    from blob_storage import add_to_queue
    result = add_to_queue("topic", "short", "url", "thumb", {}, "text", 60)
    assert result is None
