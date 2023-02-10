from discord import ApplicationCommandError

class InvalidMessage(ApplicationCommandError, Exception):
    pass

class MogiNotFound(ApplicationCommandError, Exception):
    pass

class InvalidRankInput(ApplicationCommandError, Exception):
    pass

class NotBackable(ApplicationCommandError, Exception):
    pass

class NotAddable(ApplicationCommandError, Exception):
    pass

class MogiArchived(ApplicationCommandError, Exception):
    pass

class InvalidTag(ApplicationCommandError, Exception):
    pass

class OutOfRange(ApplicationCommandError, Exception):
    pass

class InvalidFile(ApplicationCommandError, Exception):
    pass