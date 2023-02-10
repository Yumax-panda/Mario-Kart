from discord import ApplicationCommandError
from errors import MyError

class TimeNotSelected(ApplicationCommandError, MyError):
    pass

class HourNotAddable(ApplicationCommandError, MyError):
    pass

class NotGathering(ApplicationCommandError, MyError):
    pass