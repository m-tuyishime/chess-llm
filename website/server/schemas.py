from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(populate_by_name=True)

class HealthResponse(BaseSchema):
    """Response schema for health check."""
    status: str
