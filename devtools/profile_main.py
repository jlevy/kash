"""
Quick profiler, helpful to monitor startup time etc.
"""

import cProfile
import pstats

from kash.shell.shell_main import main


def entrypoint():
    main()


if __name__ == "__main__":
    cProfile.run("entrypoint()", "python_profile")

    p = pstats.Stats("python_profile")
    p.sort_stats("time").print_stats(30)
