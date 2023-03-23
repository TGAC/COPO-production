__author__ = 'felix.shaw@tgac.ac.uk - 29/07/2016'


class CopoRuntimeError(RuntimeError):

    def __init__(self, message, errors=dict()):

        # Call the base class constructor with the parameters it needs
        super(CopoRuntimeError, self).__init__(message)

        self.errors = errors
