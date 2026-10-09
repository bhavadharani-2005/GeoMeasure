from typing import Literal

from pydantic import BaseModel


class Measurement(BaseModel):
    type: Literal["area", "length"]
    value: float
    unit: str
