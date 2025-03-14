import glob
from pathlib import Path

from kash.config.logger import get_logger
from kash.exec_model.commands_model import CommentedCommand
from kash.exec_model.script_model import Script
from kash.help.help_types import RecipeScript, RecipeSnippet

log = get_logger(__name__)

RECIPE_EXT = ".ksh"

RECIPES_DIR = Path(__file__).parent / "recipes"


def load_recipe_scripts() -> tuple[list[RecipeScript], list[CommentedCommand]]:
    """
    Load and parse all snippets from all recipe scripts.
    """

    recipe_files = sorted(glob.glob(str(RECIPES_DIR / f"*{RECIPE_EXT}")))

    scripts: list[RecipeScript] = []
    for recipe_file in recipe_files:
        try:
            # Get recipe name without .md extension
            recipe_name = Path(recipe_file).stem

            # Read and parse the file
            with open(recipe_file) as f:
                content = f.read()
                script = Script.parse(content)
                scripts.append(RecipeScript(recipe_name, script))

            log.debug("Loaded recipe script: %s", recipe_file)
        except Exception as e:
            log.warning("Failed to parse recipe file %s: %s", recipe_file, e)

    log.info("Loaded %d recipe scripts", len(scripts))

    all_snippets = [c for script in scripts for c in script.all_snippets()]

    return (scripts, all_snippets)


def load_recipe_snippets() -> list[RecipeSnippet]:
    _scripts, snippets = load_recipe_scripts()
    return [RecipeSnippet(command=snippet) for snippet in snippets]
