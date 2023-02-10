from discord import ApplicationCommandError

class EmptyResult(ApplicationCommandError, Exception):
    pass

class InvalidScoreInput(ApplicationCommandError, Exception):
    pass

class InvalidIdInput(ApplicationCommandError, Exception):
    pass

class IdOutOfRange(ApplicationCommandError, Exception):
    pass

class NotCSVFile(ApplicationCommandError, Exception):
    pass

class NotAcceptableContent(ApplicationCommandError, Exception):
    pass