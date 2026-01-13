from click import option, Context, pass_context, argument, UNPROCESSED, group
from loguru import logger
from typing import Generator, cast
from types import SimpleNamespace
from pathlib import Path
import sys

from .types import OptionalPrefixAndFilePath, Variable, Variables, Command, ExportTarget, VariableVisibility, VariableType
from .click import (
    OPTIONAL_PREFIX_AND_FILE_PATH,
    KEY_VALUE,
    to_list,
    to_dict,
)
from .variables import (
    load_variables,
    dump_variables,
    encrypt_variables,
    decrypt_variables,
    execute_with_variables,
    export_variables,
    set_variable,
    encrypt_variable,
)

from .spi import (
    list_factories,
    Backend,
)


@group()
@option(
    "--backend",
    "-b",
    "backend_name",
    type=str,
    required=False,
    default="dummy",
)
@option(
    "--backend-config",
    "-c",
    "backend_config",
    multiple=True,
    type=KEY_VALUE,
    callback=to_dict,
)
@pass_context
def app(
    context: Context, 
    backend_name: str, 
    backend_config: dict[str, str],
    # optional_prefixes_and_variables_file_paths: list[OptionalPrefixAndVariableFilePath],
) -> None:
    logger.debug("App started! ")
    context.obj = SimpleNamespace()
    
    factories = list_factories()
    factory = next((f for f in factories if f.name == backend_name), None)
    assert factory is not None, f"Backend '{backend_name}' not found. Available backends: {[f.name for f in factories]}"
    config = factory.parse_config(backend_config)
    context.obj.backend = context.with_resource(factory.create_backend(config))
    
        


@app.command()
@argument("file_path", type=Path, required=True)
@pass_context
def encrypt(context: Context, file_path: Path) -> None:
    backend = cast(Backend, context.obj.backend)

    variables = load_variables(file_path)
    variables = encrypt_variables(backend, variables)
    dump_variables(variables, file_path)



@app.command()
@argument("file_path", type=Path, required=True)
@pass_context
def decrypt(context: Context, file_path: Path) -> None:
    backend = cast(Backend, context.obj.backend)
    
    variables = load_variables(file_path)
    variables = decrypt_variables(backend, variables)
    dump_variables(variables, file_path)



@app.command()
@option(
    "--variables",
    "-v",
    "optional_prefixes_and_file_paths",
    type=OPTIONAL_PREFIX_AND_FILE_PATH,
    multiple=True,
    callback=to_list,
)
@option(
    "--auto-prefixes",
    "-a",
    "auto_prefixes",
    is_flag=True,
    default=False,
)
@argument(
    "command",
    type=UNPROCESSED,
    required=True,
    nargs=-1,
    callback=to_list,
)
@pass_context
def exec(
    context: Context, 
    command: Command, 
    optional_prefixes_and_file_paths: list[OptionalPrefixAndFilePath],
    auto_prefixes: bool,
) -> None:
    backend = cast(Backend, context.obj.backend)
    
    def yield_variables() -> Generator[Variable, None, None]:
        for optional_prefix, file_path in optional_prefixes_and_file_paths:
            if optional_prefix is None and auto_prefixes:
                optional_prefix = file_path.stem.upper()
                
            variables = load_variables(file_path)
            variables = variables.with_prefix(prefix) if ( prefix := optional_prefix ) is not None else variables
            variables = decrypt_variables(backend, variables)
            yield from variables
    
    variables = Variables(yield_variables())

    execute_with_variables(command, variables)



@app.command()
@option(
    "--target",
    "-t",
    "target",
    type=ExportTarget,
    required=True,
)
@option(
    "--config",
    "-c",
    "config",
    multiple=True,
    type=KEY_VALUE,
    callback=to_dict,
)
@argument("file_path", type=Path, required=True)
@pass_context
def export(context: Context, file_path: Path, target: ExportTarget, config: dict[str, str]) -> None:
    backend = cast(Backend, context.obj.backend)

    variables = load_variables(file_path)
    variables = decrypt_variables(backend, variables)
    output = export_variables(variables, target, config)
    print(output)


@app.command()
@option(
    "--variables",
    "-v",
    "file_path",
    type=Path,
    required=True,
)
@option(
    "--visibility",
    type=VariableVisibility,
    required=False,
)
@option(
    "--type",
    "variable_type",
    type=VariableType,
    required=False,
)
@argument("variable_name", type=str, required=True)
@argument("variable_value", type=str, required=True)
@pass_context
def set(
    context: Context,
    file_path: Path,
    variable_name: str,
    variable_value: str,
    visibility: VariableVisibility | None,
    variable_type: VariableType | None,
) -> None:
    backend = cast(Backend, context.obj.backend)
    # Read from stdin if value is "-"
    if variable_value == "-":
        variable_value = sys.stdin.read()

    # Load existing variables
    variables = load_variables(file_path)

    # Set the variable
    variables = set_variable(
        variables,
        name=variable_name,
        value=variable_value,
        visibility=visibility,
        type=variable_type,
    )

    # Encrypt if visibility is secret
    final_var = variables.by_name(variable_name)
    if final_var and final_var.visibility == VariableVisibility.SECRET:
        # Encrypt just this variable
        encrypted_var = encrypt_variable(backend, final_var)
        # Replace in list
        variables = Variables([encrypted_var if v.name == variable_name else v for v in variables])

    # Write back to file
    dump_variables(variables, file_path)