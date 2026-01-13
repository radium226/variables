from click import ParamType, Context, Parameter
from typing import Any
from pathlib import Path

from .types import OptionalPrefixAndFilePath, KeyValue


class OptionalPrefixAndFilePathParamType(ParamType):
    name = "optional_prefix_and_file_path"

    def convert(self, value: Any, param: Parameter | None, ctx: Context | None) -> OptionalPrefixAndFilePath:
        try:
            assert isinstance(value, str), f"Expected a string value, got {type(value).__name__}"
            if "=" in value:
                prefix_str, file_path_str = value.split("=", 1)
                prefix = prefix_str.strip() or None
            else:
                prefix = None
                file_path_str = value

            file_path = Path(file_path_str.strip())
            assert file_path.is_file(), f"File does not exist or is not a file: {file_path_str!r}"

            return (prefix, file_path)
        except Exception as e:
            self.fail(
                f"{e}",
                param,
                ctx,
            )


OPTIONAL_PREFIX_AND_FILE_PATH = OptionalPrefixAndFilePathParamType()


def to_list(ctx: Context, param: Parameter, value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value)



class KeyValueParamType(ParamType):
    name = "tuple"

    def convert(self, value: Any, param: Parameter | None, ctx: Context | None) -> KeyValue:
        try:
            assert isinstance(value, str), f"Expected a string value, got {type(value).__name__}"
            [key, value] = value.split("=", 1)
            return KeyValue(key.strip(), value.strip())
        except Exception as e:
            self.fail(
                f"{e}",
                param,
                ctx,
            )


KEY_VALUE = KeyValueParamType()


def to_dict(ctx: Context, param: Parameter, value: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if value is None:
        return result
    for key_value in value:
        result[key_value.key] = key_value.value
    return result