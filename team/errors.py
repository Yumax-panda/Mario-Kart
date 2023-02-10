from discord import ApplicationCommandError

class LoungeError(ApplicationCommandError):
    pass

class PlayerNotFound(LoungeError):
    pass

class RoleNotFound(Exception):
    pass

class MessageNotFound(Exception):
    pass

class NotAuthorized(Exception):
    pass

class AuthorNotFound(Exception):
    pass