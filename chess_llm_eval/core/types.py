from typing import Literal, TypeAlias

Color: TypeAlias = Literal["white", "black"]
Fen: TypeAlias = str
SanMove: TypeAlias = str
UciMove: TypeAlias = str

# Game outcome types
PuzzleOutcome: TypeAlias = Literal["success", "failure"]
