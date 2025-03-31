from collections.abc import Iterable
from textwrap import dedent

from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger
from kash.exec.combiners import Combiner
from kash.model.actions_model import Action, ActionInput, ActionResult, ExecContext
from kash.model.items_model import Item, State
from kash.model.params_model import RawParamValues
from kash.model.paths_model import StorePath
from kash.utils.common.task_stack import task_stack
from kash.utils.common.type_utils import not_none
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


def look_up_actions(action_names: Iterable[str]) -> list[type[Action]]:
    from kash.exec.action_registry import look_up_action_class

    return [look_up_action_class(action_name) for action_name in action_names]


@dataclass
class SequenceAction(Action):
    """
    A sequential action that chains the outputs of each action to the inputs of the next.
    """

    action_names: tuple[str, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        if not self.action_names or len(self.action_names) <= 1:
            raise InvalidInput(
                f"Action must have at least two sub-actions: {self.name}: {self.action_names}"
            )

        extra_desc = "This action is a sequence of these actions: " + ", ".join(
            f"`{name}`" for name in self.action_names
        )
        self.description = dedent(self.description)
        seq_description = (
            "\n\n".join([self.description, extra_desc]) if self.description else extra_desc
        )
        self.description = seq_description

    def run(self, input: ActionInput, context: ExecContext) -> ActionResult:
        from kash.exec.action_exec import run_action_with_shell_context
        from kash.workspaces import current_ws

        items = input.items
        with task_stack().context(
            self.name, total_parts=len(self.action_names), unit="sequence step"
        ) as ts:
            look_up_actions(self.action_names)  # Validate action names.

            log.message("Begin action sequence `%s`", self.name)

            original_input_paths = [StorePath(not_none(item.store_path)) for item in items]
            transient_outputs: list[Item] = []

            for i, action_name in enumerate(self.action_names):
                for item in items:
                    if not item.store_path:
                        raise InvalidInput("Item must have a store path: %s", item)

                log.message(
                    "Action sequence `%s` step %s/%s: `%s`",
                    self.name,
                    i + 1,
                    len(self.action_names),
                    action_name,
                )

                item_paths = [not_none(item.store_path) for item in items]

                # Output of this action is transient if it's not the last action.
                last_action = i == len(self.action_names) - 1
                output_state = None if last_action else State.transient

                # Run this action.
                result = run_action_with_shell_context(
                    action_name, RawParamValues(), *item_paths, override_state=output_state
                )

                # Track transient items and archive them if all actions succeed.
                for item in result.items:
                    if item.state == State.transient:
                        transient_outputs.append(item)

                # Results are the input to the next action in the sequence.
                items = result.items

                ts.next()

            # The final items should be derived from the original inputs.
            for item in items:
                if item.store_path in original_input_paths:
                    # Special case in case an action does nothing to an item.
                    log.info("Result item is an original input: %s", item.store_path)
                else:
                    item.update_relations(derived_from=original_input_paths)

            log.message("Action sequence `%s` complete. Archiving transient items.", self.name)
            ws = current_ws()
            for item in transient_outputs:
                try:
                    ws.archive(StorePath(not_none(item.store_path)))
                except FileNotFoundError:
                    log.info("Item to archive not found, moving on: %s", item.store_path)

        return ActionResult(items)


@dataclass
class ComboAction(Action):
    """
    An action that combines the results of other actions.
    """

    action_names: tuple[str, ...] = ()

    combiner: Combiner | None = None

    def __post_init__(self):
        super().__post_init__()
        if not self.action_names or len(self.action_names) <= 1:
            raise InvalidInput(
                f"Action must have at least two sub-actions: {self.name}: {self.action_names}"
            )

        extra_desc = "This action is a combination of these actions: " + ", ".join(
            f"`{name}`" for name in self.action_names
        )
        combo_description = (
            "\n\n".join([self.description, extra_desc]) if self.description else extra_desc
        )

        self.description = combo_description

    def run(self, input: ActionInput, context: ExecContext) -> ActionResult:
        from kash.exec.action_exec import run_action_with_shell_context
        from kash.exec.combiners import combine_as_paragraphs

        with task_stack().context(
            self.name, total_parts=len(self.action_names), unit="combo part"
        ) as ts:
            look_up_actions(self.action_names)  # Validate action names.

            for item in input.items:
                if not item.store_path:
                    raise InvalidInput("Item must have a store path: %s", item)

            item_paths = [not_none(item.store_path) for item in input.items]

            results: list[ActionResult] = []

            for i, action_name in enumerate(self.action_names):
                log.message(
                    "Action combo `%s` part %s/%s: %s",
                    self.name,
                    i + 1,
                    len(self.action_names),
                    action_name,
                )

                result = run_action_with_shell_context(
                    action_name, RawParamValues(), *item_paths, override_state=State.transient
                )

                results.append(result)

                ts.next()

            combiner = self.combiner or combine_as_paragraphs
            combined_result = combiner(input.items, results)

        log.message(
            "Combined output of %s actions on %s inputs: %s",
            len(results),
            len(input.items),
            combined_result,
        )
        log.debug("Combined result metadata: %s", combined_result.metadata())

        return ActionResult([combined_result])
