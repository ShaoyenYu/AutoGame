from typing import Union, List, Tuple


class CyclicQueue:
    def __init__(self, it: Union[str, List[str], Tuple]):
        self.it = tuple(self._do_split(it))
        self.length = len(self.it)
        self.it_cyclic = self.as_iter()

    @staticmethod
    def _do_split(it):
        if isinstance(it, str):
            it = it.split(",")
        if all(x.isnumeric() for x in it):
            return [int(x) for x in it]
        return it

    def as_iter(self):
        i = 0
        while True:
            yield self.it[i]
            i = (i + 1) % self.length

    def next(self):
        return next(self.it_cyclic)
