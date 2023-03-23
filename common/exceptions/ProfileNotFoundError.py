__author__ = 'felix.shaw@tgac.ac.uk - 24/03/2016'


class ProfileNotFoundError(RuntimeError):

    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(ProfileNotFoundError, self).__init__(message)
