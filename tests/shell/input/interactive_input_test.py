#!/usr/bin/env python3
"""
Interactive test for comparing InquirerPy and questionary input prompt implementations.

This demonstrates all the features of both implementations and can be run manually
to test the look and feel of the interface.

Run with: uv run python tests/shell/input/interactive_input_test.py
"""

import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def choose_implementation() -> str:
    """Let user choose which implementation to test."""
    print("INPUT PROMPT IMPLEMENTATION COMPARISON")
    print("=" * 60)
    print("Choose which implementation to test:")
    print("1. InquirerPy (current implementation)")
    print("2. Questionary (new implementation)")
    print("3. Both (side by side comparison)")
    print("=" * 60)

    while True:
        choice = input("Enter your choice (1/2/3): ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("Invalid choice. Please enter 1, 2, or 3.")


def get_implementations(choice: str) -> list[tuple[str, Any]]:
    """Get the implementation modules based on user choice."""
    implementations = []

    if choice in ["1", "3"]:
        try:
            from kash.shell.input import input_prompts

            implementations.append(("InquirerPy", input_prompts))
        except ImportError as e:
            print(f"Could not import InquirerPy implementation: {e}")

    if choice in ["2", "3"]:
        try:
            from kash.shell.input import input_prompts_questionary

            implementations.append(("Questionary", input_prompts_questionary))
        except ImportError as e:
            print(f"Could not import Questionary implementation: {e}")

    if not implementations:
        print("No implementations available!")
        sys.exit(1)

    return implementations


def demo_simple_string_input(impl_name: str, module: Any) -> dict[str, Any]:
    """Test simple string input with various options."""
    print(f"\n=== TESTING SIMPLE STRING INPUT ({impl_name}) ===")

    results = {}

    # Basic string input
    print(f"\n• Basic string input ({impl_name})")
    results["basic"] = module.input_simple_string("Enter your name")

    # String with default
    print(f"\n• String with default ({impl_name})")
    results["with_default"] = module.input_simple_string("Enter your city", default="San Francisco")

    # String with validation
    print(f"\n• String with validation ({impl_name})")

    def validate_email(value: str) -> bool | str:
        if not value:
            return "Email is required"
        if "@" not in value:
            return "Please enter a valid email address"
        if "." not in value.split("@")[1]:
            return "Email must have a valid domain"
        return True

    results["with_validation"] = module.input_simple_string(
        "Enter your email", validate=validate_email, instruction="Must be a valid email address"
    )

    # Non-required input
    print(f"\n• Optional input ({impl_name})")
    results["optional"] = module.input_simple_string(
        "Enter optional notes", required=False, instruction="Optional - press Enter to skip"
    )

    # Multiline input
    print(f"\n• Multiline input ({impl_name})")
    results["multiline"] = module.input_simple_string(
        "Enter a description",
        multiline=True,
        # Don't pass instruction - let it use the default multiline instruction
    )

    return results


def demo_confirm_input(impl_name: str, module: Any) -> dict[str, Any]:
    """Test confirm input."""
    print(f"\n=== TESTING CONFIRM INPUT ({impl_name}) ===")

    results = {}

    # Basic confirm
    print(f"\n• Basic confirm ({impl_name})")
    results["basic"] = module.input_confirm("Do you want to continue?")

    # Confirm with default True
    print(f"\n• Confirm with default True ({impl_name})")
    results["default_true"] = module.input_confirm(
        "Enable notifications?", default=True, instruction="Default is Yes"
    )

    # Confirm with default False
    print(f"\n• Confirm with default False ({impl_name})")
    results["default_false"] = module.input_confirm(
        "Delete all files?", default=False, instruction="Default is No - be careful!"
    )

    return results


def demo_choice_input(impl_name: str, module: Any) -> dict[str, Any]:
    """Test choice selection."""
    print(f"\n=== TESTING CHOICE INPUT ({impl_name}) ===")

    results = {}

    # Basic choice
    print(f"\n• Basic choice ({impl_name})")
    languages = ["Python", "JavaScript", "Go", "Rust", "TypeScript", "Java", "C++"]
    results["language"] = module.input_choice(
        "Select your favorite programming language",
        choices=languages,
        instruction="Use arrow keys to navigate",
    )

    # Choice with default
    print(f"\n• Choice with default ({impl_name})")
    colors = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"]
    results["color"] = module.input_choice(
        "Select a color", choices=colors, default="Blue", instruction="Default is Blue"
    )

    # Optional choice (can be cancelled)
    print(f"\n• Optional choice ({impl_name})")
    priorities = ["Low", "Medium", "High", "Critical"]
    results["priority"] = module.input_choice(
        "Select priority level (optional)",
        choices=priorities,
        mandatory=False,
        instruction="This choice is optional - can be cancelled",
    )

    return results


def demo_checkbox_input(impl_name: str, module: Any) -> dict[str, Any]:
    """Test checkbox selection."""
    print(f"\n=== TESTING CHECKBOX INPUT ({impl_name}) ===")

    results = {}

    # Basic checkboxes
    print(f"\n• Basic checkboxes ({impl_name})")
    frameworks = ["React", "Vue", "Angular", "Svelte", "Solid", "Lit"]
    results["frameworks"] = module.input_checkboxes(
        "Select frameworks you've used",
        choices=frameworks,
        instruction="Space to select/deselect, Enter to confirm",
    )

    # Checkboxes with defaults
    print(f"\n• Checkboxes with defaults ({impl_name})")
    features = ["Dark mode", "Notifications", "Auto-save", "Offline mode", "Sync"]
    defaults = ["Dark mode", "Auto-save"]
    results["features"] = module.input_checkboxes(
        "Select features to enable",
        choices=features,
        default=defaults,
        instruction="Some features are pre-selected",
    )

    return results


def demo_password_input(impl_name: str, module: Any) -> dict[str, Any]:
    """Test password input."""
    print(f"\n=== TESTING PASSWORD INPUT ({impl_name}) ===")

    results = {}

    # Basic password
    print(f"\n• Basic password ({impl_name})")
    results["basic"] = module.input_password("Enter a password")

    # Password with validation
    print(f"\n• Password with validation ({impl_name})")

    def validate_password(value: str) -> bool | str:
        if len(value) < 8:
            return "Password must be at least 8 characters"
        if not any(c.isupper() for c in value):
            return "Password must contain at least one uppercase letter"
        if not any(c.islower() for c in value):
            return "Password must contain at least one lowercase letter"
        if not any(c.isdigit() for c in value):
            return "Password must contain at least one number"
        return True

    results["validated"] = module.input_password(
        "Enter a strong password",
        validate=validate_password,
        instruction="Must be 8+ chars with upper, lower, and number",
    )

    # Optional password
    print(f"\n• Optional password ({impl_name})")
    results["optional"] = module.input_password(
        "Enter optional API key", required=False, instruction="Optional - press Enter to skip"
    )

    return results


def demo_file_path_input(impl_name: str, module: Any) -> dict[str, Any]:
    """Test file path input."""
    print(f"\n=== TESTING FILE PATH INPUT ({impl_name}) ===")

    results = {}

    # Basic file path
    print(f"\n• Basic file path ({impl_name})")
    results["basic"] = module.input_file_path("Select a file")

    # File path with validation
    print(f"\n• File path with validation ({impl_name})")

    def validate_python_file(value: str) -> bool | str:
        if not value:
            return "Please select a file"
        if not value.endswith(".py"):
            return "Please select a Python file (.py)"
        return True

    results["python_file"] = module.input_file_path(
        "Select a Python file", validate=validate_python_file, instruction="Must be a .py file"
    )

    # Optional file path
    print(f"\n• Optional file path ({impl_name})")
    results["optional"] = module.input_file_path(
        "Select optional config file", required=False, instruction="Optional - press Enter to skip"
    )

    return results


def print_results(results: dict[str, dict[str, Any]]) -> None:
    """Print all collected results."""
    print("\n" + "=" * 80)
    print("COLLECTED RESULTS")
    print("=" * 80)

    for impl_name, impl_results in results.items():
        print(f"\nRESULTS FOR {impl_name.upper()}:")
        print("-" * 40)

        for category, data in impl_results.items():
            print(f"\n  {category.upper().replace('_', ' ')}:")
            for key, value in data.items():
                if value is None:
                    print(f"    {key}: (cancelled)")
                elif (
                    isinstance(value, str)
                    and key in ["basic", "validated"]
                    and "password" in category
                ):
                    # Hide password values
                    print(f"    {key}: {'*' * len(value)} (hidden)")
                elif isinstance(value, list):
                    print(f"    {key}: {value}")
                else:
                    print(f"    {key}: {value}")


def run_tests_for_implementation(impl_name: str, module: Any) -> dict[str, Any]:
    """Run all tests for a specific implementation."""
    print(f"\nSTARTING TESTS FOR {impl_name}")
    print("=" * 60)
    print("Keyboard controls:")
    print("  - Esc: Cancel single question (returns to test)")
    print("  - Ctrl+C: Cancel entire test session")
    print("Test each feature and observe the differences.")
    print("=" * 60)

    impl_results = {}

    try:
        # Test each input type
        impl_results["string_input"] = demo_simple_string_input(impl_name, module)
        impl_results["confirm_input"] = demo_confirm_input(impl_name, module)
        impl_results["choice_input"] = demo_choice_input(impl_name, module)
        impl_results["checkbox_input"] = demo_checkbox_input(impl_name, module)
        impl_results["password_input"] = demo_password_input(impl_name, module)
        impl_results["file_path_input"] = demo_file_path_input(impl_name, module)

        print(f"\nAll tests completed for {impl_name}!")

    except KeyboardInterrupt:
        print(f"\n\nTests cancelled by user for {impl_name}.")

    return impl_results


def main() -> None:
    """Run interactive tests."""
    # Choose implementation
    choice = choose_implementation()
    implementations = get_implementations(choice)

    all_results = {}

    try:
        # Run tests for each chosen implementation
        for impl_name, module in implementations:
            impl_results = run_tests_for_implementation(impl_name, module)
            all_results[impl_name] = impl_results

            # If testing both, ask if user wants to continue to next
            if len(implementations) > 1 and impl_name != implementations[-1][0]:
                print("\n" + "=" * 60)
                continue_choice = (
                    input(f"Continue to test {implementations[1][0]}? (y/n): ").strip().lower()
                )
                if continue_choice != "y":
                    break
                print("\n")

        # Print comparison results
        print_results(all_results)

        # Show comparison summary if both were tested
        if len(all_results) > 1:
            print("\n" + "=" * 80)
            print("COMPARISON SUMMARY")
            print("=" * 80)
            print("Both implementations should provide:")
            print("- Consistent API signatures")
            print("- Same validation behavior")
            print("- Proper keyboard interrupt handling")
            print("- Multiline input support")
            print("- All advanced features (password, file path)")
            print()
            print("Key differences to note:")
            print("- Multiline end sequence (questionary: Ctrl+D, InquirerPy: Esc+Enter)")
            print("- Visual styling may differ slightly")
            print("- Error message formatting may vary")

    except KeyboardInterrupt:
        print("\n\nTests cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during testing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
