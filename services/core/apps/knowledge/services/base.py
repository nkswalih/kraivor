class KnowledgeSpaceServiceError(Exception):
    pass


class KnowledgePermissionError(KnowledgeSpaceServiceError):
    pass


class KnowledgeSpaceNotFoundError(KnowledgeSpaceServiceError):
    pass
