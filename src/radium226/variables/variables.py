from typing import overload, Generator, Any
from pathlib import Path
import yaml
from subprocess import run, CompletedProcess
from base64 import b64encode, b64decode
from loguru import logger
from os import environ
from contextlib import ExitStack
from io import StringIO
import shlex
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables

from .types import (
    Variable,
    Variables,
    VariableVisibility,
    Command,
    VariableType,
    ExportTarget,
    VariableNotEncryptedError,
)

from .files import create_temp_file
from .types import VariableName, VariableValue
from .spi import Backend



ENCRYPTION_PREFIX = "encrypted:"



@overload
def load_variables(file_path: Path, /) -> Variables: ...



@overload
def load_variables(text: str, /) -> Variables: ...



def load_variables(text_or_file_path: Path | str, /) -> Variables:
    if isinstance(text_or_file_path, Path):
        text = text_or_file_path.read_text(encoding="utf-8")
    else:
        text = text_or_file_path

    obj = yaml.safe_load(text)

    def yield_variables() -> Generator[Variable, None, None]:
        for variable_obj in obj["variables"]:
            variable_name = variable_obj["name"]
            variable_value = variable_obj["value"]
            variable_visibility = VariableVisibility(variable_obj.get("visibility", "plain"))
            variable_type = VariableType(variable_obj.get("type", "text"))
            variable = Variable(
                name=variable_name,
                value=variable_value,
                visibility=variable_visibility,
                type=variable_type,
            )
            if variable_value != "":
                yield variable
            else:
                logger.warning(f"Variable {variable_name!r} has empty value. Skipping variable.")

    return Variables(yield_variables())



def encrypt_variable(backend: Backend, variable: Variable) -> Variable:
    if variable.visibility != VariableVisibility.SECRET:
        return variable

    if variable.value.startswith(ENCRYPTION_PREFIX):
        logger.warning(f"Variable {variable.name!r} is already encrypted. Skipping encryption.")
        return variable

    variable_value = ENCRYPTION_PREFIX + b64encode(backend.encrypt_value(variable.value.encode("utf-8"))).decode("utf-8")
    return variable.with_value(variable_value)


def decrypt_variable(backend: Backend, variable: Variable, *, raise_when_not_encrypted: bool = False) -> Variable:
    if variable.visibility != VariableVisibility.SECRET:
        return variable

    if not variable.value.startswith(ENCRYPTION_PREFIX):
        if raise_when_not_encrypted:
            raise VariableNotEncryptedError(variable.name)
        logger.warning(f"Variable {variable.name!r} is not encrypted. Skipping decryption.")
        return variable

    variable_value = variable.value[len(ENCRYPTION_PREFIX):]
    variable_value_bytes = b64decode(variable_value.encode("utf-8"))
    variable_value = backend.decrypt_value(variable_value_bytes).decode("utf-8")
    return variable.with_value(variable_value)



def encrypt_variables(backend: Backend, variables: Variables) -> Variables:
    return Variables(
        encrypt_variable(backend, variable)
        for variable in variables
    )



def decrypt_variables(backend: Backend, variables: Variables, *, raise_when_not_encrypted: bool = False) -> Variables:
    def yield_decrypted_variables() -> Generator[Variable, None, None]:
        for variable in variables:
            decrypted_variable = decrypt_variable(backend, variable, raise_when_not_encrypted=raise_when_not_encrypted)
            if decrypted_variable.value != "":
                yield decrypted_variable
            else:
                logger.warning(f"Variable {variable.name!r} has empty value after decryption. Skipping variable.")

    return Variables(yield_decrypted_variables())


@overload
def dump_variables(variables: Variables) -> str:...



@overload
def dump_variables(variables: Variables, file_path: Path) -> None: ...


def dump_variables(variables: Variables, file_path: Path | None = None) -> str | None:
    obj = {
        "variables": [
            {
                "name": variable.name,
                "value": variable.value,
                "visibility": variable.visibility.value,
                "type": variable.type.value,
            }
            for variable in variables
        ]
    }
    content = "---\n"
    content += yaml.dump(obj)
    if file_path is not None:
        file_path.write_text(content, encoding="utf-8")
        return None
    else:
        return content
    

def export_variables(variables: Variables, target: ExportTarget, config: dict[str, str]) -> str:
    match target:
        case ExportTarget.KUBECTL:
            variables_for_secret: list[Variable] = []
            variables_for_configmap: list[Variable] = []
            for variable in variables:
                if variable.type != VariableType.TEXT:
                    logger.warning(f"Variable {variable.name!r} has type {variable.type!r} which is not supported for kubectl export. Skipping variable.")
                    continue

                if variable.visibility == VariableVisibility.SECRET:
                    variables_for_secret.append(variable)
                else:
                    variables_for_configmap.append(variable)

            configmap_name = config.get("configmap_name") or config.get("name") or "variables"
            configmap = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": configmap_name
                },
                "data": {
                    variable.name: variable.value
                    for variable in variables_for_secret
                },
            }

            secret_name = config.get("secret_name") or config.get("name") or "variables"
            secret = {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": secret_name
                },
                "data": {
                    variable.name: b64encode(variable.value.encode("utf-8")).decode("utf-8")
                    for variable in variables_for_secret
                },
            }

            buffer = StringIO()
            for manifest_obj in [configmap, secret]:
                print("---", file=buffer)
                print(yaml.dump(manifest_obj, default_flow_style=False, sort_keys=False), file=buffer)

            return buffer.getvalue()
        
        case ExportTarget.BASH:
            lines = []
            for variable in variables:
                if variable.type != VariableType.TEXT:
                    logger.warning(f"Variable {variable.name!r} has type {variable.type!r} which is not supported for bash export. Skipping variable.")
                    continue
                value = shlex.quote(variable.value)
                line = f'export {variable.name}="{value}"'
                lines.append(line)

            return "\n".join(lines)
        
        case _:
            raise NotImplementedError(f"Export target {target} is not implemented yet.")



def execute_with_variables(command: Command, variables: Variables, **kwargs: Any) -> CompletedProcess:
    variable_values_by_name: dict[str, str] = {}
    exit_stack = ExitStack()
    try:
        for variable in variables:
            if variable.visibility == VariableVisibility.SECRET and variable.value.startswith(ENCRYPTION_PREFIX):
                logger.warning(f"Variable {variable.name!r} is still encrypted. It should be decrypted before execution.")
                continue

            variable_name = variable.name if variable.prefix is None else f"{variable.prefix}_{variable.name}"
            match variable.type:
                case VariableType.FILE:
                    temp_file_path = exit_stack.enter_context(create_temp_file(variable.value))
                    logger.debug("Writing variable {variable_name!r} to temporary file {temp_file_path}", variable_name=variable_name, temp_file_path=temp_file_path)
                    variable_values_by_name[variable_name] = str(temp_file_path)

                case VariableType.TEXT:
                    variable_values_by_name[variable_name] = variable.value

        
        command, variable_values_by_name = _interpolate_command(command, variable_values_by_name)

        logger.debug(f"{variable_values_by_name=}")


        env = {
            **environ,
            **variable_values_by_name,
        }

        return run(
            command,
            env=env,
            check=True,
            **kwargs,
        )
    finally:
        exit_stack.close()


def set_variable(
    variables: Variables,
    name: VariableName,
    value: VariableValue,
    visibility: VariableVisibility | None = None,
    type: VariableType | None = None,
) -> Variables:
    """
    Set a variable's value, creating it if it doesn't exist.

    Args:
        variables: Existing variables list
        name: Variable name to set
        value: New value
        visibility: Optional visibility override
        type: Optional type override

    Returns:
        Updated Variables list with modified/new variable
    """
    existing = variables.by_name(name)

    if existing is not None:
        # Update existing variable
        new_variable = Variable(
            name=name,
            value=value,
            visibility=visibility if visibility is not None else existing.visibility,
            type=type if type is not None else existing.type,
        )
        # Replace the existing variable
        return Variables([new_variable if v.name == name else v for v in variables])
    else:
        # Create new variable with defaults
        new_variable = Variable(
            name=name,
            value=value,
            visibility=visibility if visibility is not None else VariableVisibility.PLAIN,
            type=type if type is not None else VariableType.TEXT,
        )
        # Append to list
        return Variables(list(variables) + [new_variable])
    

def _interpolate_command(command: Command, variable_values_by_name: dict[str, str]) -> tuple[Command, dict[str, str]]:
    environment = Environment()
    asts = [environment.parse(arg) for arg in command]
    code_types = [environment.compile(ast, name="<command>", filename="<command>") for ast in asts]
    templates = [environment.template_class.from_code(environment, code_type, environment.globals) for code_type in code_types]
    variable_names_going_to_be_used = [
        variable_name
        for ast in asts
        for variable_name in find_undeclared_variables(ast)
    ]

    logger.debug("The variables that are going to be used are: {variable_names}", variable_names=list(variable_names_going_to_be_used))

    command = [
        template.render(**variable_values_by_name)
        for template in templates
    ]

    variable_values_by_name = {
        variable_name: variable_value
        for variable_name, variable_value in variable_values_by_name.items()
        if variable_name not in variable_names_going_to_be_used
    }

    return command, variable_values_by_name
