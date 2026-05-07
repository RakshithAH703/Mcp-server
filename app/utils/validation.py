from flask import request
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_query(model: type[BaseModel]):
    return model.model_validate(dict(request.args))


def validate_json(model: type[BaseModel]):
    payload = request.get_json(silent=True) or {}
    return model.model_validate(payload)
