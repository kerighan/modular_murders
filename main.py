import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from genotype import *
from suspect import Case

n_suspects = 6
case = Case(n_suspects)
# print(pd.DataFrame(suspects.data()))


# G = suspects.to_graph()
# suspects.draw()

# index 0 is always murderer
