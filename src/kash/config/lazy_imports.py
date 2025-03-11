import time

import_start_time = time.time()

# TODO: Find a better way to improve startup time by delaying importing of big packages.
# Tried these but none seem quite like what we need?
# https://pypi.org/project/apipkg/
# https://scientific-python.org/specs/spec-0001/
# https://github.com/scientific-python/lazy-loader
# https://pypi.org/project/lazy-import/
# https://pypi.org/project/lazy-imports/

# Also tried lazyasd's background importing but it didn't speed up anything
# and intermittentlly causes errors.

# from lazyasd import load_module_in_background
# load_module_in_background("wikipedia")
# load_module_in_background("tenacity")
# load_module_in_background("deepgram")
# load_module_in_background("numpy")
# load_module_in_background("pandas")
# load_module_in_background("weasyprint")
