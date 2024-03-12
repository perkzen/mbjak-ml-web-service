from pydantic import BaseModel


class PredictBikesDTO(BaseModel):
    available_bike_stands: int
    apparent_temperature: float
    surface_pressure: float
    temperature: float
    dew_point: float
