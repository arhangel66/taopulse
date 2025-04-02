from pydantic import Field, BaseModel


class BaseResponse(BaseModel):
    is_success: bool = Field(default=True)
    message: str | None = None
    duration: float | None = None
