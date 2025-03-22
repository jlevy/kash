import signal
import sys
import threading
import traceback
from functools import cache


def current_stack_traces(all_threads: bool = True) -> str:
    """
    Return current stack traces as a string.
    """

    stack_traces = []
    main_thread_id = threading.get_ident()

    if all_threads:
        frames = sys._current_frames()
        main_thread_trace = frames.pop(main_thread_id, None)
    else:
        frames = {}
        main_thread_trace = sys._current_frames()[main_thread_id]

    if main_thread_trace:
        stack_traces.append(f"\nThread ID: {main_thread_id} (main thread)\n")
        stack_traces.append("".join(traceback.format_stack(main_thread_trace)))

    for thread_id, stack_frame in frames.items():
        stack_traces.append(f"\nThread ID: {thread_id}\n")
        stack_traces.append("".join(traceback.format_stack(stack_frame)))

    return "".join(stack_traces)


def dump_stack_traces(all_threads: bool = True, file=sys.stderr):
    print(current_stack_traces(all_threads), file=file)


def _dump_stack_traces_handler(signum, _frame, file=sys.stderr):
    print(f"\n\nReceived signal {signum}, will dump stack traces:", file=file)
    dump_stack_traces()


@cache
def add_stacktrace_handler(sig=signal.SIGUSR1):
    """
    To use (with USR1): `pkill -USR1 -f 'module_name'`. Can also use SIGQUIT.
    """

    signal.signal(sig, _dump_stack_traces_handler)
