"""
a class to be inherited for printing reasons
"""
class Printable:
    def __repr__(self):
        return str(self.__dict__)
