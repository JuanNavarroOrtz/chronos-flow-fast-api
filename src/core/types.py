from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Decimal in Python, plain JSON number on the wire.
Number = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
