# Generate README.md from the doc files.

reformat --inplace src/kash/docs/markdown/topics/*.md src/kash/docs/markdown/*.md

format_markdown_template \
  src/kash/docs/markdown/topics/a1_what_is_kash.md \
  src/kash/docs/markdown/topics/a2_progress.md \
  src/kash/docs/markdown/topics/a3_installation.md \
  src/kash/docs/markdown/topics/a4_getting_started.md \
  src/kash/docs/markdown/topics/a5_tips_for_use_with_other_tools.md \
  src/kash/docs/markdown/topics/a6_development.md \
  --md_template=src/kash/docs/markdown/readme_template.md --rerun

save --no_frontmatter --to=README.md
