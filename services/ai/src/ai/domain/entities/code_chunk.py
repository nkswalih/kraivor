from dataclasses import dataclass


@dataclass
class CodeChunk:
    file_path: str
    content: str
    language: str
    repo_id: str
    workspace_id: str
    line_start: int = 0
    line_end: int = 0
    score: float = 0.0
    token_count: int = 0
