"""
Pydantic v2 compatible wrapper around bson.ObjectId, used only inside
models/ (the Mongo document layer). Schemas exposed over the API always
serialize ids as plain strings — see schemas/*.py.
"""
from typing import Any

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [core_schema.str_schema(), core_schema.no_info_plain_validator_function(cls.validate)]
                    ),
                ]
            ),
            # IMPORTANT: only stringify in JSON mode. In Python mode (used by
            # model_dump(by_alias=True) before a Mongo insert/update), keep
            # the real bson.ObjectId — otherwise `_id` gets written to Mongo
            # as a string and every ObjectId-based lookup silently stops
            # matching.
            serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json"),
        )

    @classmethod
    def validate(cls, value: str) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid ObjectId: {value}")
        return ObjectId(value)
