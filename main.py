"""Generate a case and print it. Usage: python main.py [seed]"""

import sys
from pprint import pprint

from suspect import Case

case = Case(seed=int(sys.argv[1]) if len(sys.argv) > 1 else None)
print(f"{case.n_suspects} suspects, murderer is #0: {case.murderer}")
print("clues:", case.clues)
print("alibis:", case.alibis)
pprint(case.environment)
# case.draw()  # traits -> suspects graph, needs matplotlib
