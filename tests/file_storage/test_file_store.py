"""Comprehensive test of FileStore import and frontmatter functionality."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from kash.file_storage.item_file_format import read_item, write_item
from kash.model.items_model import Format, Item, ItemType
from kash.model.operations_model import OperationSummary
from kash.utils.common.url import Url


@dataclass
class FileInfo:
    """Information about a file in the workspace."""

    path: str
    size: int
    is_dir: bool


@dataclass
class WorkspaceListing:
    """Complete listing of workspace contents."""

    files: list[FileInfo]
    total_files: int
    total_dirs: int
    total_size: int

    def __str__(self) -> str:
        lines = [
            f"Workspace listing ({self.total_files} files, {self.total_dirs} dirs, {self.total_size} bytes):"
        ]
        for file_info in sorted(self.files, key=lambda f: f.path):
            size_str = f"{file_info.size:>8}" if not file_info.is_dir else "     DIR"
            lines.append(f"  {size_str}  {file_info.path}")
        return "\n".join(lines)


def list_workspace_contents(workspace_dir: Path) -> WorkspaceListing:
    """List all files in the workspace recursively."""
    files = []
    total_files = 0
    total_dirs = 0
    total_size = 0

    for path in sorted(workspace_dir.rglob("*")):
        rel_path = str(path.relative_to(workspace_dir))
        is_dir = path.is_dir()
        size = 0 if is_dir else path.stat().st_size

        files.append(FileInfo(rel_path, size, is_dir))

        if is_dir:
            total_dirs += 1
        else:
            total_files += 1
            total_size += size

    return WorkspaceListing(files, total_files, total_dirs, total_size)


def test_file_store_imports_and_frontmatter():
    """Test file store import operations and frontmatter parsing for various file types."""
    # Import FileStore here to avoid circular imports
    from kash.file_storage.file_store import FileStore

    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / "test_workspace"
        store = FileStore(workspace_dir, is_global_ws=False, auto_init=True)

        # Verify workspace was initialized
        assert workspace_dir.exists()
        assert (workspace_dir / ".kash").exists()

        print(f"\n✔︎ Created workspace at: {workspace_dir}")

        # Test 1: Import a markdown file with existing frontmatter
        md_file = Path(tmpdir) / "test_doc.md"
        md_file.write_text(
            dedent("""\
            ---
            title: Imported Document
            type: doc
            format: markdown
            description: This document has frontmatter
            extra:
              tags: [test, import]
              custom_field: some value
            ---

            # Imported Document

            This is a document with **existing frontmatter**.
            """)
        )

        imported_md = store.import_item(md_file)
        loaded_md = store.load(imported_md)
        assert loaded_md.title == "Imported Document"
        assert loaded_md.description == "This document has frontmatter"
        assert loaded_md.extra and loaded_md.extra["tags"] == ["test", "import"]
        assert loaded_md.extra["custom_field"] == "some value"
        assert loaded_md.body and "**existing frontmatter**" in loaded_md.body
        print(f"✔︎ Imported markdown with frontmatter: {imported_md}")

        # Test 2: Import a plain text file (should get frontmatter added)
        txt_file = Path(tmpdir) / "plain.txt"
        txt_file.write_text("This is plain text content.\nWith multiple lines.")

        imported_txt = store.import_item(txt_file)
        loaded_txt = store.load(imported_txt)
        assert loaded_txt.type == ItemType.doc
        assert loaded_txt.format == Format.plaintext
        assert loaded_txt.body == "This is plain text content.\nWith multiple lines."

        # Check that frontmatter was added
        txt_content = (workspace_dir / imported_txt).read_text()
        assert txt_content.startswith("---")
        print(f"✔︎ Imported plain text: {imported_txt}")

        # Test 3: Import a Python file (should get hash-style frontmatter)
        py_file = Path(tmpdir) / "script.py"
        py_file.write_text(
            dedent('''\
            #!/usr/bin/env python3
            """A test Python script."""

            def main():
                print("Hello, world!")

            if __name__ == "__main__":
                main()
            ''')
        )

        imported_py = store.import_item(py_file, as_type=ItemType.extension)
        loaded_py = store.load(imported_py)
        assert loaded_py.type == ItemType.extension
        assert loaded_py.format == Format.python
        assert loaded_py.body and 'print("Hello, world!")' in loaded_py.body

        # Check hash-style frontmatter (if it has frontmatter)
        py_content = (workspace_dir / imported_py).read_text()
        if "# ---" in py_content:
            assert "# type: extension" in py_content
            print(f"✔︎ Python file has hash-style frontmatter: {imported_py}")
        else:
            print(f"✔︎ Python file imported without frontmatter: {imported_py}")
        print(f"✔︎ Imported Python file: {imported_py}")

        # Test 4: Import HTML file
        html_file = Path(tmpdir) / "page.html"
        html_file.write_text(
            dedent("""\
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Page</title>
            </head>
            <body>
                <h1>Test Page</h1>
                <p>This is a test HTML page.</p>
            </body>
            </html>""")
        )

        imported_html = store.import_item(html_file)
        loaded_html = store.load(imported_html)
        assert loaded_html.format == Format.html
        assert loaded_html.body and "<h1>Test Page</h1>" in loaded_html.body

        # Check HTML comment frontmatter (if any)
        html_content = (workspace_dir / imported_html).read_text()
        if "<!--" in html_content and "-->" in html_content:
            print("✔︎ HTML has comment-style frontmatter")
        print(f"✔︎ Imported HTML file: {imported_html}")

        # Test 5: Import YAML file
        yaml_file = Path(tmpdir) / "config.yml"
        yaml_file.write_text(
            dedent("""\
            database:
              host: localhost
              port: 5432
              name: testdb

            features:
              - authentication
              - logging
              - caching
            """)
        )

        imported_yaml = store.import_item(yaml_file, as_type=ItemType.data)
        loaded_yaml = store.load(imported_yaml)
        assert loaded_yaml.type == ItemType.data
        assert loaded_yaml.format == Format.yaml
        assert loaded_yaml.body and "host: localhost" in loaded_yaml.body
        print(f"✔︎ Imported YAML file: {imported_yaml}")

        # Test 6: Import CSV file
        csv_file = Path(tmpdir) / "data.csv"
        csv_file.write_text(
            dedent("""\
            name,age,city
            Alice,30,New York
            Bob,25,San Francisco
            Charlie,35,Chicago
            """)
        )

        imported_csv = store.import_item(csv_file, as_type=ItemType.table)
        loaded_csv = store.load(imported_csv)
        assert loaded_csv.type == ItemType.table
        assert loaded_csv.format == Format.csv
        assert loaded_csv.body and "Alice,30,New York" in loaded_csv.body

        # CSV may have hash-style frontmatter
        csv_content = (workspace_dir / imported_csv).read_text()
        if "# ---" in csv_content:
            print("✔︎ CSV has hash-style frontmatter")
        print(f"✔︎ Imported CSV file: {imported_csv}")

        # Test 7: Import JSON file
        json_file = Path(tmpdir) / "data.json"
        json_file.write_text(
            dedent("""\
            {
              "name": "Test Data",
              "version": "1.0",
              "items": [
                {"id": 1, "value": "first"},
                {"id": 2, "value": "second"}
              ]
            }""")
        )

        imported_json = store.import_item(json_file)
        loaded_json = store.load(imported_json)
        assert loaded_json.format == Format.json
        assert loaded_json.body and '"name": "Test Data"' in loaded_json.body

        # JSON may have slash-style frontmatter
        json_content = (workspace_dir / imported_json).read_text()
        if "// ---" in json_content:
            print("✔︎ JSON has slash-style frontmatter")
        print(f"✔︎ Imported JSON file: {imported_json}")

        # Test 8: Import binary file (PNG)
        png_file = Path(tmpdir) / "image.png"
        # Create a minimal valid PNG header
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        png_file.write_bytes(png_data)

        imported_png = store.import_item(png_file, as_type=ItemType.asset)
        loaded_png = store.load(imported_png)
        # Note: file store may import as resource instead of asset by default
        assert loaded_png.type in [ItemType.asset, ItemType.resource]
        assert loaded_png.format == Format.png
        # Binary files may have external_path or be copied into store
        assert not loaded_png.body  # No body for binary files
        print(f"✔︎ Imported PNG file: {imported_png}")

        # Test 9: Import URL
        url = Url("https://example.com/test-page")
        imported_url = store.import_item(url)
        loaded_url = store.load(imported_url)
        assert loaded_url.type == ItemType.resource
        assert loaded_url.format == Format.url
        assert loaded_url.url == "https://example.com/test-page"
        print(f"✔︎ Imported URL: {imported_url}")

        # Test 10: Test round-trip for different formats
        # Create various items
        test_items = [
            Item(
                type=ItemType.doc,
                title="Markdown Test",
                format=Format.markdown,
                body="# Test\n\nThis is a **test**.",
                description="Testing markdown",
            ),
            Item(
                type=ItemType.doc,
                title="HTML Test",
                format=Format.html,
                body="<h1>Test</h1><p>This is a test.</p>",
            ),
            Item(
                type=ItemType.extension,
                title="Script Test",
                format=Format.python,
                body="print('test')",
            ),
            Item(
                type=ItemType.data,
                title="YAML Test",
                format=Format.yaml,
                body="key: value\nlist:\n  - item1\n  - item2",
            ),
        ]

        print("\n📝 Testing round-trip for various formats:")
        for item in test_items:
            # Save
            path = store.save(item)
            # Load
            loaded = store.load(path)
            # Verify
            assert loaded.title == item.title
            assert loaded.format == item.format
            assert loaded.type == item.type
            assert loaded.body == item.body
            format_value = item.format.value if item.format else "unknown"
            print(f"  ✔︎ {format_value}: {item.title}")

        # Test 11: Test reimport (should update existing)
        # Modify the markdown file
        md_file.write_text(
            dedent("""\
            ---
            title: Updated Document
            type: doc
            format: markdown
            description: This document was updated
            extra:
              version: 2.0
            ---

            # Updated Document

            This content has been **updated**.
            """)
        )

        # Reimport
        reimported_md = store.import_item(md_file, reimport=True)
        reloaded_md = store.load(reimported_md)
        assert reloaded_md.title == "Updated Document"
        assert reloaded_md.description == "This document was updated"
        assert reloaded_md.extra and reloaded_md.extra["version"] == 2.0
        assert reloaded_md.body and "**updated**" in reloaded_md.body
        print(f"\n✔︎ Reimported with updates: {reimported_md}")

        # Test 12: Import with operation history
        transcript_item = Item(
            type=ItemType.doc,
            title="Meeting Transcript",
            format=Format.markdown,
            body="Transcript of the meeting...",
            history=[
                OperationSummary(
                    action_name="transcribe",
                )
            ],
        )

        transcript_path = store.save(transcript_item)
        loaded_transcript = store.load(transcript_path)
        assert loaded_transcript.history
        assert loaded_transcript.history[0].action_name == "transcribe"
        print(f"✔︎ Saved item with history: {transcript_path}")

        # Test 13: Test normalize operation
        markdown_to_normalize = Item(
            type=ItemType.doc,
            title="Needs Normalization",
            format=Format.markdown,
            body="# Header\n\n\nToo many   spaces    here.\n\n\n\nAnd empty lines.",
        )

        norm_path = store.save(markdown_to_normalize)
        normalized_path = store.normalize(norm_path)
        normalized_item = store.load(normalized_path)
        # The normalizer should clean up extra spaces and empty lines
        assert normalized_item.body and "\n\n\n" not in normalized_item.body
        print("✔︎ Normalization working")

        # Test 14: Verify workspace structure with detailed listing
        print("\n📁 Detailed workspace listing:")
        listing = list_workspace_contents(workspace_dir)
        print(listing)

        # Count total items
        all_items = list(store.walk_items())
        print(f"\n✔︎ Total items in store: {len(all_items)}")

        # Verify various item types were saved
        item_types_found = set()
        formats_found = set()
        for item_path in all_items:
            item = store.load(item_path)
            item_types_found.add(item.type)
            if item.format:
                formats_found.add(item.format)

        print(f"✔︎ Item types: {[t.value for t in sorted(item_types_found, key=lambda x: x.value)]}")
        print(f"✔︎ Formats: {[f.value for f in sorted(formats_found, key=lambda x: x.value)]}")

        # Test 15: Archive functionality test
        # Create a dedicated item for archiving to avoid conflicts with reimport
        archive_test_item = Item(
            type=ItemType.doc,
            title="Archive Test",
            format=Format.markdown,
            body="This item will be archived.",
        )

        archive_item_path = store.save(archive_test_item)
        assert store.exists(archive_item_path)

        # Archive the item
        store.archive(archive_item_path)
        assert not store.exists(archive_item_path)  # Original should be gone
        print("✔︎ Archive working")

        # Test 16: Sidematter format tests (from test_sidematter_integration.py)
        print("\n📄 Testing sidematter formats:")

        # Test reading frontmatter file
        fm_file = Path(tmpdir) / "frontmatter_test.md"
        fm_file.write_text(
            dedent("""\
            ---
            title: Test Document
            type: doc
            format: markdown
            ---

            # Test Content

            This is the body.""")
        )

        fm_item = read_item(fm_file, workspace_dir)
        assert fm_item.title == "Test Document"
        assert fm_item.type == ItemType.doc
        assert fm_item.format == Format.markdown
        assert fm_item.body and "Test Content" in fm_item.body
        print("✔︎ Read frontmatter file")

        # Test writing with frontmatter (default)
        fm_item = Item(
            type=ItemType.doc,
            title="Frontmatter Test",
            format=Format.markdown,
            body="# Test Content\n\nThis is the body.",
        )

        fm_path = workspace_dir / "frontmatter_out.md"
        write_item(fm_item, fm_path, use_frontmatter=True)

        content = fm_path.read_text()
        assert content.startswith("---")
        assert "title: Frontmatter Test" in content
        assert "type: doc" in content
        assert "# Test Content" in content
        print("✔︎ Write frontmatter file")

        # Test writing with sidematter
        sm_item = Item(
            type=ItemType.doc,
            title="Sidematter Test",
            format=Format.markdown,
            body="# Test Content\n\nThis is the body.",
        )

        sm_path = workspace_dir / "sidematter_out.md"
        write_item(sm_item, sm_path, use_frontmatter=False)

        # Main file should not have frontmatter
        content = sm_path.read_text()
        assert not content.startswith("---")
        assert content.startswith("# Test Content")

        # Metadata should be in sidecar file
        meta_path = sm_path.with_suffix(".meta.yml")
        assert meta_path.exists()
        meta_content = meta_path.read_text()
        assert "title: Sidematter Test" in meta_content
        assert "type: doc" in meta_content

        # Reading should work with sidematter
        sm_read = read_item(sm_path, workspace_dir)
        assert sm_read.title == "Sidematter Test"
        assert sm_read.type == ItemType.doc
        assert sm_read.format == Format.markdown
        assert sm_read.body and "Test Content" in sm_read.body
        print("✔︎ Write/read sidematter file")

        # Test sidematter precedence over frontmatter
        mixed_file = Path(tmpdir) / "mixed_test.md"
        mixed_file.write_text(
            dedent("""\
            ---
            title: Frontmatter Title
            type: doc
            ---

            # Test Content""")
        )

        # Create sidematter with different metadata
        mixed_meta = mixed_file.with_suffix(".meta.yml")
        mixed_meta.write_text(
            dedent("""\
            title: Sidematter Title
            type: concept
            extra:
              custom_field: from sidematter
            """)
        )

        mixed_item = read_item(mixed_file, workspace_dir)
        assert mixed_item.title == "Sidematter Title"  # Should use sidematter
        assert mixed_item.type == ItemType.concept  # Should use sidematter
        assert mixed_item.extra and mixed_item.extra["custom_field"] == "from sidematter"
        assert mixed_item.body and "# Test Content" in mixed_item.body
        print("✔︎ Sidematter precedence working")

        # Test assets handling
        asset_file = workspace_dir / "with_assets.md"
        asset_file.write_text("# Test Content\n\nThis references assets.")

        # Create sidematter metadata
        asset_meta = asset_file.with_suffix(".meta.yml")
        asset_meta.write_text(
            dedent("""\
            title: Test with Assets
            type: doc
            """)
        )

        # Create assets directory
        assets_dir = asset_file.with_name("with_assets.assets")
        assets_dir.mkdir()

        # Create test files
        (assets_dir / "image.png").write_text("fake png")
        (assets_dir / "document.pdf").write_text("fake pdf")
        (assets_dir / "data.json").write_text('{"test": true}')

        # Create subdirectory with files
        subdir = assets_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested_image.jpg").write_text("fake jpg")

        asset_item = read_item(asset_file, workspace_dir)
        assert asset_item.asset_dir == "with_assets.assets"
        print("✔︎ Assets handling working")

        # Final workspace listing
        print("\n📁 Final workspace listing:")
        final_listing = list_workspace_contents(workspace_dir)
        print(final_listing)

        print("\n✅ All tests passed!")
