from enum import Enum


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class SessionStatus(str, Enum):
    created = "created"
    deployed = "deployed"
    destroyed = "destroyed"
    finished = "finished"
    validated = "validated"
    error = "error"
