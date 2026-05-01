def test_root_serves_spa_shell_with_expected_frontend_assets(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.get("/")

    assert response.status_code == 200
    assert "SimplyNarrated - Turn Documents Into Audiobooks, Locally" in response.text
    assert '/static/js/views/player.js' in response.text
    assert '/static/js/views/upload.js' in response.text
    assert '/static/js/app.js' in response.text


def test_player_script_exposes_chapter_edit_and_reconvert_hooks(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.get("/static/js/views/player.js")

    assert response.status_code == 200
    assert "saveChapterTextEdits" in response.text
    assert "reconvertCurrentChapter" in response.text
    assert "Save + Reconvert" in response.text


def test_frontend_scripts_use_safe_text_rendering_for_dynamic_book_data(app_client):
    client, _data_dir, _library_dir = app_client

    dashboard = client.get("/static/js/views/dashboard.js")
    player = client.get("/static/js/views/player.js")
    progress = client.get("/static/js/views/progress.js")

    assert dashboard.status_code == 200
    assert player.status_code == 200
    assert progress.status_code == 200

    assert "function createLibraryBookCard(book)" in dashboard.text
    assert 'onclick="deleteBook' not in dashboard.text
    assert "titleEl.textContent = title" in dashboard.text
    assert "message.textContent = entry.message || \"\"" in progress.text
    assert "titleEl.textContent = chapter.title || `Chapter ${chapter.number}`;" in player.text


def test_progress_view_scripts_include_teardown_hooks(app_client):
    client, _data_dir, _library_dir = app_client

    progress = client.get("/static/js/views/progress.js")
    app = client.get("/static/js/app.js")

    assert progress.status_code == 200
    assert app.status_code == 200

    assert "function teardownProgressView()" in progress.text
    assert "teardownProgressView();" in progress.text
    assert 'state.currentView === "progress"' in app.text
    assert 'typeof teardownProgressView === "function"' in app.text


def test_upload_view_no_longer_advertises_markdown_support(app_client):
    client, _data_dir, _library_dir = app_client

    response = client.get("/static/js/views/upload.js")

    assert response.status_code == 200
    assert "Supports: TXT, PDF, ZIP" in response.text
    assert 'accept=".txt,.pdf,.zip"' in response.text
    assert "TXT, MD, PDF, or ZIP" not in response.text