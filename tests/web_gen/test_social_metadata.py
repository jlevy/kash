from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def test_social_metadata_with_full_data():
    """Test that social metadata is correctly rendered when all data is provided."""
    template_dir = Path(__file__).parent.parent.parent / "src" / "kash" / "web_gen" / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("base_webpage.html.jinja")

    social_meta = {
        "title": "Custom Social Title",
        "description": "A compelling description for social sharing",
        "image": "https://example.com/image.jpg",
        "url": "https://example.com/my-page",
        "type": "article",
        "site_name": "My Site",
        "twitter_handle": "myhandle",
    }

    rendered = template.render(
        title="Page Title", content="<p>Test content</p>", social_meta=social_meta
    )

    # Test OpenGraph tags
    assert 'property="og:title" content="Custom Social Title"' in rendered
    assert (
        'property="og:description" content="A compelling description for social sharing"'
        in rendered
    )
    assert 'property="og:image" content="https://example.com/image.jpg"' in rendered
    assert 'property="og:url" content="https://example.com/my-page"' in rendered
    assert 'property="og:type" content="article"' in rendered
    assert 'property="og:site_name" content="My Site"' in rendered

    # Test Twitter Card tags
    assert 'name="twitter:card" content="summary_large_image"' in rendered
    assert 'name="twitter:title" content="Custom Social Title"' in rendered
    assert (
        'name="twitter:description" content="A compelling description for social sharing"'
        in rendered
    )
    assert 'name="twitter:image" content="https://example.com/image.jpg"' in rendered
    assert 'name="twitter:site" content="@myhandle"' in rendered


def test_social_metadata_with_minimal_data():
    """Test that social metadata works with minimal data, using fallbacks."""
    template_dir = Path(__file__).parent.parent.parent / "src" / "kash" / "web_gen" / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("base_webpage.html.jinja")

    social_meta = {"description": "Just a description"}

    rendered = template.render(
        title="Page Title", content="<p>Test content</p>", social_meta=social_meta
    )

    # Should use page title as fallback for og:title and twitter:title
    assert 'property="og:title" content="Page Title"' in rendered
    assert 'name="twitter:title" content="Page Title"' in rendered

    # Should include provided description
    assert 'property="og:description" content="Just a description"' in rendered
    assert 'name="twitter:description" content="Just a description"' in rendered

    # Should use default type
    assert 'property="og:type" content="website"' in rendered

    # Should not include optional tags that weren't provided
    assert 'property="og:image"' not in rendered
    assert 'property="og:url"' not in rendered
    assert 'property="og:site_name"' not in rendered
    assert 'name="twitter:image"' not in rendered
    assert 'name="twitter:site"' not in rendered


def test_social_metadata_graceful_omission():
    """Test that no social metadata is rendered when social_meta is not provided."""
    template_dir = Path(__file__).parent.parent.parent / "src" / "kash" / "web_gen" / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("base_webpage.html.jinja")

    rendered = template.render(
        title="Page Title",
        content="<p>Test content</p>",
        # No social_meta provided
    )

    # Should not include any social metadata tags
    assert 'property="og:' not in rendered
    assert 'name="twitter:' not in rendered
    assert "<!-- Open Graph meta tags -->" not in rendered
    assert "<!-- Twitter Card meta tags -->" not in rendered

    template_dir = Path(__file__).parent.parent.parent / "src" / "kash" / "web_gen" / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("base_webpage.html.jinja")

    rendered = template.render(
        title="Page Title",
        content="<p>Test content</p>",
        social_meta={},  # Empty dict should be falsy
    )

    # Should not include any social metadata tags
    assert 'property="og:' not in rendered
    assert 'name="twitter:' not in rendered
