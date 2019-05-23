# errors.py


class GenericError(Exception):

    def __init__(self, message):
        super(GenericError, self).__init__(message)
        self.message = message


class InputError(GenericError):

    def __init__(self, message):
        super(InputError, self).__init__(message)


class AlreadyExistsError(GenericError):
    def __init__(self, message):
        super(GenericError, self).__init__(message)


class NotFoundError(GenericError):
    def __init__(self, message):
        super(GenericError, self).__init__(message)


class ExternalServiceError(GenericError):

    def __init__(self, message):
        super(ExternalServiceError, self).__init__(message)


class ServerError(GenericError):

    def __init__(self, message):
        super(GenericError, self).__init__(message)