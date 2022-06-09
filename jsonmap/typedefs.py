"""
This is just to avoid circular imports...
"""

from typing import Any, Dict, List, Literal

# once we have recursive types in mypy, we should switch to this definition
# Json = str | float | List["Json"] | Dict[str, "Json"] | Literal[None]
Json = str | float | List[Any] | Dict[str, Any] | Literal[None]
