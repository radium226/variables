import pytest
from pathlib import Path
from loguru import logger
from click.testing import CliRunner
import tempfile

from radium226.variables import (
    Variables,
    Variable,
    load_variables,
    encrypt_variables,
    decrypt_variables,
    VariableVisibility,
    VariableType,
    execute_with_variables,
    set_variable,
    app,
    dump_variables,
    Backend,
)

from radium226.variables.backends.dummy import Dummy


@pytest.fixture
def decrypted_variables() -> Variables:
    file_path = Path(__file__).parent / "samples" / "decrypted.yaml"
    return load_variables(file_path)


@pytest.fixture
def encrypted_variables() -> Variables:
    file_path = Path(__file__).parent / "samples" / "encrypted.yaml"
    return load_variables(file_path)


@pytest.fixture
def backend() -> Backend:
    return Dummy()



def test_encrypt_and_decrypt(backend: Backend, decrypted_variables: Variables) -> None:
    variables = decrypted_variables
    for _ in range(5):  # Test idempotency
        logger.debug("Encrypting variables...")
        variables = encrypt_variables(backend, variables)
        for variable in variables:
            if variable.visibility == VariableVisibility.SECRET:
                assert variable.value.startswith("encrypted:")
            else:
                assert not variable.value.startswith("encrypted:")
            
    
    for _ in range(5):  # Test idempotency
        logger.debug("Decrypting variables...")
        variables = decrypt_variables(backend, variables)
        for variable in variables:
            assert not variable.value.startswith("encrypted:")
            decrypted_variable = decrypted_variables.by_name(variable.name)
            assert decrypted_variable is not None
            assert variable.value == decrypted_variable.value

def test_execute_with(decrypted_variables: Variables) -> None:
    process = execute_with_variables(
        variables=decrypted_variables,
        command=["python", "-c", "import os; print(os.getenv('FOO')); print(os.getenv('BAR')); print(os.getenv('CONFIG'))"],
        capture_output=True,
        text=True
    )

    stdout = process.stdout
    logger.debug(f"Process stdout:\n{stdout}")

    assert "foo" in stdout
    assert "bar" in stdout
    assert "settings" not in stdout  # CONFIG is a file, its content should not appear in stdout


def test_execute_with_interpolated_command(decrypted_variables: Variables) -> None:
    process = execute_with_variables(
        variables=decrypted_variables,
        command=["python", "-c", "import os; print(os.getenv('FOO')); print(os.getenv('BAR')); print('{{ CONFIG }}'); print('WIN!' if os.getenv('CONFIG') is None else 'LOSE!')"],
        capture_output=True,
        text=True
    )

    stdout = process.stdout
    logger.debug(f"Process stdout:\n{stdout}")

    assert "foo" in stdout
    assert "bar" in stdout
    assert "/tmp" in stdout
    assert "WIN!" in stdout


def test_set_variable_creates_new_with_defaults() -> None:
    """Test creating a new variable with default visibility (plain) and type (text)."""
    variables = Variables([
        Variable(name="EXISTING", value="old_value", visibility=VariableVisibility.PLAIN, type=VariableType.TEXT)
    ])

    result = set_variable(variables, name="NEW_VAR", value="new_value")

    # Should have both variables
    assert len(result) == 2

    # New variable should exist with defaults
    new_var = result.by_name("NEW_VAR")
    assert new_var is not None
    assert new_var.value == "new_value"
    assert new_var.visibility == VariableVisibility.PLAIN
    assert new_var.type == VariableType.TEXT

    # Existing variable should be unchanged
    existing_var = result.by_name("EXISTING")
    assert existing_var is not None
    assert existing_var.value == "old_value"


def test_set_variable_updates_existing_value_only() -> None:
    """Test updating an existing variable's value while preserving its properties."""
    variables = Variables([
        Variable(name="MY_VAR", value="old_value", visibility=VariableVisibility.SECRET, type=VariableType.FILE)
    ])

    result = set_variable(variables, name="MY_VAR", value="new_value")

    # Should still have one variable
    assert len(result) == 1

    # Variable should have new value but same properties
    updated_var = result.by_name("MY_VAR")
    assert updated_var is not None
    assert updated_var.value == "new_value"
    assert updated_var.visibility == VariableVisibility.SECRET
    assert updated_var.type == VariableType.FILE


def test_set_variable_with_explicit_visibility_and_type() -> None:
    """Test creating/updating with explicit visibility and type."""
    variables = Variables([
        Variable(name="EXISTING", value="old_value", visibility=VariableVisibility.PLAIN, type=VariableType.TEXT)
    ])

    # Create new variable with explicit properties
    result = set_variable(
        variables,
        name="NEW_SECRET",
        value="secret_value",
        visibility=VariableVisibility.SECRET,
        type=VariableType.FILE
    )

    new_var = result.by_name("NEW_SECRET")
    assert new_var is not None
    assert new_var.value == "secret_value"
    assert new_var.visibility == VariableVisibility.SECRET
    assert new_var.type == VariableType.FILE

    # Update existing variable with changed properties
    result = set_variable(
        result,
        name="EXISTING",
        value="new_value",
        visibility=VariableVisibility.SECRET,
        type=VariableType.FILE
    )

    updated_var = result.by_name("EXISTING")
    assert updated_var is not None
    assert updated_var.value == "new_value"
    assert updated_var.visibility == VariableVisibility.SECRET
    assert updated_var.type == VariableType.FILE


def test_cli_set_command() -> None:
    """Test the CLI set command updates the YAML file correctly."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        variables_file = tmpdir_path / "variables.yaml"
        
        # Create initial variables file
        initial_vars = Variables([
            Variable(name="EXISTING", value="old_value", visibility=VariableVisibility.PLAIN, type=VariableType.TEXT)
        ])
        dump_variables(initial_vars, variables_file)

        # Run set command to add new variable
        result = runner.invoke(app, [
            "-b", "dummy",
            "set",
            "-v", str(variables_file),
            "NEW_VAR",
            "new_value"
        ])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Load and verify
        updated_vars = load_variables(variables_file)
        assert len(updated_vars) == 2

        new_var = updated_vars.by_name("NEW_VAR")
        assert new_var is not None
        assert new_var.value == "new_value"
        assert new_var.visibility == VariableVisibility.PLAIN
        assert new_var.type == VariableType.TEXT


def test_cli_set_command_with_stdin() -> None:
    """Test the CLI set command reads value from stdin when '-' is provided."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        variables_file = tmpdir_path / "variables.yaml"
        
        # Create initial variables file
        initial_vars = Variables([])
        dump_variables(initial_vars, variables_file)

        # Run set command with stdin
        secret_value = "my-secret-password"
        result = runner.invoke(app, [
            "-b", "dummy",
            "set",
            "-v", str(variables_file),
            "PASSWORD",
            "-"
        ], input=secret_value)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Load and verify
        updated_vars = load_variables(variables_file)
        assert len(updated_vars) == 1

        password_var = updated_vars.by_name("PASSWORD")
        assert password_var is not None
        assert password_var.value == secret_value
        assert password_var.visibility == VariableVisibility.PLAIN
        assert password_var.type == VariableType.TEXT


def test_cli_set_command_auto_encrypts_secrets(backend: Backend) -> None:
    """Test that setting a variable with visibility=secret automatically encrypts it."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        variables_file = tmpdir_path / "variables.yaml"
        
        # Create initial variables file
        initial_vars = Variables([])
        dump_variables(initial_vars, variables_file)

        # Run set command with visibility=secret
        secret_value = "super-secret-password"
        result = runner.invoke(app, [
            "-b", "dummy",
            "set",
            "-v", str(variables_file),
            "--visibility", "secret",
            "API_KEY",
            secret_value
        ])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Load and verify it's encrypted
        updated_vars = load_variables(variables_file)
        assert len(updated_vars) == 1

        api_key_var = updated_vars.by_name("API_KEY")
        assert api_key_var is not None
        assert api_key_var.visibility == VariableVisibility.SECRET
        # Should be encrypted (starts with "encrypted:")
        assert api_key_var.value.startswith("encrypted:"), f"Expected encrypted value, got: {api_key_var.value}"

        # Verify we can decrypt it back to the original value
        decrypted_vars = decrypt_variables(backend, updated_vars)
        decrypted_var = decrypted_vars.by_name("API_KEY")
        assert decrypted_var is not None
        assert decrypted_var.value == secret_value