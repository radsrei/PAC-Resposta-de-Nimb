from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Modelo base: snake_case no Python, camelCase no JSON (contrato do front React)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
