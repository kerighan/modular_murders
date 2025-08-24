"""Simple entry point that constructs a case for manual experimentation."""

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from suspect import Case

case = Case()
# The following lines are handy for manual debugging and exploration.
# print(pd.DataFrame(suspects.data()))


# G = suspects.to_graph()
# suspects.draw()

# index 0 is always murderer
