"""
This is just to avoid circular imports...
"""

from typing import Any, Dict, List, Literal

# once we have recursive types in mypy, we should switch to this definition
# Json = str | float | List["Json"] | Dict[str, "Json"] | Literal[None]
Json = str | float | List[Any] | Dict[str, Any] | Literal[None]


def resolve(path: List[str], data: Json) -> Json:
    """fetch a value from a json object"""
    # walk down the path
    obj = data
    for field in path:
        match obj:
            case dict():
                obj = obj[field]
            case list():
                obj = obj[int(field)]
            case _:
                raise ValueError("Invalid field index")
    return obj
