from abc import ABC, abstractmethod

class ObjectiveType (ABC):
    ''' An abstract class that defines an objective function which is implemented as the method
    in which reviewers are connected to papers.   Subclasses must implement a build method which adds
    these connections to the assignment graph.
    '''

    @abstractmethod
    def build (self, assignment_graph):
        pass