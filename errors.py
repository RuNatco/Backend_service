class UserNotFoundError(Exception):
    ...


class AddNotFoundError(Exception):
    ...


class ModerationTaskNotFoundError(Exception):
    ...


class KafkaUnavailableError(Exception):
    ...


class ModerationEnqueueError(Exception):
    ...


class AccountNotFoundError(Exception):
    ...


class InvalidCredentialsError(Exception):
    ...


class AccountBlockedError(Exception):
    ...


class UnauthorizedError(Exception):
    ...
