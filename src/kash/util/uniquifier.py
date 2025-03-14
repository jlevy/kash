from typing import NamedTuple


class Key(NamedTuple):
    name: str
    group: str


class Uniquifier:
    """
    Maintain a set of unique names, adding suffixes to ensure uniqueness when needed.
    """

    def __init__(self, init_values: set[Key] | None = None, template: str = "{name}_{suffix}"):
        if init_values is None:
            init_values = set()
        if "{name}" not in template or "{suffix}" not in template:
            raise ValueError(f"Template must contain placeholders for name and suffix: {template}")

        self.keys: set[Key] = set()
        self.template = template

        if init_values:
            self.keys.update(init_values)

    def uniquify_historic(self, name: str, group: str = "") -> tuple[str, list[str]]:
        """
        Same as uniquify, but also return the list of previous names that were used.
        """
        old_names: list[str] = []

        if Key(name, group) not in self.keys:
            self.keys.add(Key(name, group))
            return name, old_names

        old_names.append(name)
        suffix = 1
        while Key(self.template.format(name=name, suffix=suffix), group) in self.keys:
            old_names.append(self.template.format(name=name, suffix=suffix))
            suffix += 1

        unique_name = self.template.format(name=name, suffix=suffix)
        self.keys.add(Key(unique_name, group))

        return unique_name, old_names

    def uniquify(self, name: str, group: str = "") -> str:
        """
        Return a name that is the same as the input whenever possible, or with a numeric suffix
        added to ensure uniqueness among all names seen so far. If group is provided, it will only
        ensure uniqueness within that group.
        """
        return self.uniquify_historic(name, group)[0]

    def add(self, name: str, group: str = "") -> None:
        """
        Add a name to the uniquifier.
        """
        self.keys.add(Key(name, group))

    def add_new(self, name: str, group: str = "") -> None:
        """
        Add a name to the uniquifier, confirming it is not already present.
        """
        if Key(name, group) in self.keys:
            raise ValueError(f"Name is already in uniquifier: {name}")

        self.keys.add(Key(name, group))

    def __len__(self) -> int:
        return len(self.keys)


## Tests


def test_uniquifier():
    uniquifier = Uniquifier()

    # Uniqueness within the same group.
    assert uniquifier.uniquify("foo") == "foo"
    assert uniquifier.uniquify_historic("bar") == ("bar", [])
    assert uniquifier.uniquify("foo") == "foo_1"
    assert uniquifier.uniquify("foo") == "foo_2"
    assert uniquifier.uniquify_historic("foo") == ("foo_3", ["foo", "foo_1", "foo_2"])

    # Uniqueness across different groups.
    assert uniquifier.uniquify("foo", "group1") == "foo"
    assert uniquifier.uniquify("foo", "group2") == "foo"

    # Uniqueness within the same group after adding a new group.
    assert uniquifier.uniquify("foo", "group1") == "foo_1"

    # Test length of uniquifier.
    assert len(uniquifier) == 8
