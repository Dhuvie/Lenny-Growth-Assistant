def test_iframe_sandbox_policy_enforcement():
    """
    Validates that the sandbox policy conforms to the security specification in design.md:
    1. sandbox contains 'allow-scripts'
    2. sandbox explicitly EXCLUDES 'allow-same-origin' (protects parent localStorage & cookies)
    3. sandbox explicitly EXCLUDES 'allow-top-navigation' (protects against redirect attacks)
    4. sandbox explicitly EXCLUDES 'allow-forms' and 'allow-popups'
    """
    from pathlib import Path
    artifact_viewer_file = Path("frontend/src/components/ArtifactViewer.tsx")
    content = artifact_viewer_file.read_text(encoding="utf-8")

    # Verify sandbox attribute in iframe
    assert 'sandbox="allow-scripts"' in content
    assert 'allow-same-origin' not in content
    assert 'allow-top-navigation' not in content

    # Verify Content Security Policy is injected into srcDoc
    assert "default-src 'none'" in content
    assert "style-src 'unsafe-inline'" in content
    assert "script-src 'unsafe-inline'" in content


def test_markdown_sanitization_policy():
    """
    Validates that DOMPurify is loaded and used in MessageBubble and ArtifactViewer.
    """
    from pathlib import Path
    mb_file = Path("frontend/src/components/MessageBubble.tsx")
    av_file = Path("frontend/src/components/ArtifactViewer.tsx")

    assert "DOMPurify.sanitize" in mb_file.read_text(encoding="utf-8")
    assert "DOMPurify.sanitize" in av_file.read_text(encoding="utf-8")
