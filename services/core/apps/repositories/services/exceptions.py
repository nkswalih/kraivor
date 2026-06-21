class RepositoryServiceError(Exception):
    pass


class RepositoryPermissionError(RepositoryServiceError):
    pass


class RepositoryNotFoundError(RepositoryServiceError):
    pass


class RepositoryAlreadyConnectedError(RepositoryServiceError):
    pass


class GitHubAuthError(RepositoryServiceError):
    pass


class GitHubAPIError(RepositoryServiceError):
    pass
