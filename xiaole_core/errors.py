class CoreError(Exception):
    """Base error for expected Core failures."""


class ConversationAccessDenied(CoreError):
    pass


class MemoryUnavailable(CoreError):
    pass


class ActionUnavailable(CoreError):
    pass


class ReminderUnavailable(CoreError):
    pass


class ModelUnavailable(CoreError):
    pass
