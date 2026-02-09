import time

import_start_time = time.time()

# TODO: Find a better way to improve startup time by delaying importing of big packages.
# Tried these but none seem quite like what we need?
# https://pypi.org/project/apipkg/
# https://scientific-python.org/specs/spec-0001/
# https://github.com/scientific-python/lazy-loader
# https://pypi.org/project/lazy-import/
# https://pypi.org/project/lazy-imports/
