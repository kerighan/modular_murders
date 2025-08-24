class DiGraph:
    def __init__(self):
        self.adj = {}
        self.pred = {}

    def add_nodes_from(self, nodes):
        for n in nodes:
            self.adj.setdefault(n, set())
            self.pred.setdefault(n, set())

    def add_edge(self, u, v):
        self.add_nodes_from([u, v])
        self.adj[u].add(v)
        self.pred[v].add(u)

    def remove_nodes_from(self, nodes):
        for n in nodes:
            for v in list(self.adj.get(n, [])):
                self.pred[v].discard(n)
            for v in list(self.pred.get(n, [])):
                self.adj[v].discard(n)
            self.adj.pop(n, None)
            self.pred.pop(n, None)

    def predecessors(self, n):
        return self.pred.get(n, set())

    def neighbors(self, n):
        return self.adj.get(n, set())


def isolates(G):
    return [n for n in G.adj if not G.adj[n] and not G.pred[n]]


def bipartite_layout(G, nodes):
    return {n: (0, 0) for n in G.adj}
