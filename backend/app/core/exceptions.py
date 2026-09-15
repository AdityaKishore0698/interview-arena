class BusinessError(Exception):
    pass

class EmailAlreadyExistsError(BusinessError):
    pass

class AccountDisabledError(BusinessError):
    pass

class InvalidCredentialsError(BusinessError):
    pass
