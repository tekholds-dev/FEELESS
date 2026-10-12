"""LEGACY NAME — `agents` is the old import name of the paper desk (paper_desk.py). Kept only so the older test files keep importing it;
no live module may import this name (tests/test_kernel_authority.py)."""
import sys

import paper_desk

sys.modules[__name__] = paper_desk
