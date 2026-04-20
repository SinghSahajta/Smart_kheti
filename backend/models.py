from pydantic import BaseModel, Field
from typing import Literal

HasIrrigation = Literal[0, 1, 2]  # 0=no, 1=yes, 2=partial
CropType = Literal["wheat", "paddy"]

class LocationIn(BaseModel):
    location_name: str = Field(..., min_length=2)
    lat: float
    lng: float

class ProfileIn(BaseModel):
    location_name: str = Field(..., min_length=2)
    lat: float
    lng: float
    crop: CropType
    sowing_date: str = Field(..., description="YYYY-MM-DD")
    has_irrigation: HasIrrigation
    farm_size_acres: float = Field(..., gt=0)
