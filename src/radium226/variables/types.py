from dataclasses import dataclass, replace
from typing import TypeAlias
from enum import StrEnum, auto
from pathlib import Path



VariableName: TypeAlias = str



VariableValue: TypeAlias = str



VariablePrefix: TypeAlias = str



class VariableVisibility(StrEnum):
    PLAIN = auto()
    SECRET = auto()


class VariableType(StrEnum):
    TEXT = auto()
    FILE = auto()




@dataclass(frozen=True, eq=True)
class Variable():
    name: VariableName
    value: VariableValue
    visibility: VariableVisibility
    prefix: VariablePrefix | None = None
    type: VariableType = VariableType.TEXT

    def with_value(self, value: VariableValue) -> "Variable":
        return replace(self, value=value)
    
    def with_prefix(self, prefix: VariablePrefix) -> "Variable":
        return replace(self, prefix=prefix)
    
    def without_prefix(self) -> "Variable":
        return replace(self, prefix=None)



class Variables(list[Variable]):
    
    def with_prefix(self, prefix: VariablePrefix) -> "Variables":
        return Variables([variable.with_prefix(prefix) for variable in self])
    
    def without_prefix(self) -> "Variables":
        return Variables([variable.without_prefix() for variable in self])
    
    def to_dict(self) -> dict[VariableName, VariableValue]:

        def variable_name(variable: Variable) -> VariableName:
            if variable.prefix is not None:
                return f"{variable.prefix}_{variable.name}"
            return variable.name

        return {variable_name(variable): variable.value for variable in self}
    
    def by_name(self, name: VariableName) -> Variable | None:
        for variable in self:
            if variable.name == name:
                return variable
        return None


OptionalPrefixAndFilePath = tuple[VariablePrefix | None, Path]


Argument: TypeAlias = str


Command: TypeAlias = list[Argument]


class ExportTarget(StrEnum):
    BASH = auto()
    ENV_FILE = auto()
    KUBECTL = auto()


@dataclass(frozen=True, eq=True)
class KeyValue():
    key: str
    value: str