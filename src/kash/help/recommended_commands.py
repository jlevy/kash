from kash.config.logger import get_logger

log = get_logger(__name__)

STANDARD_SHELL_COMMANDS = {
    # Core navigation and file operations
    "ls",
    "cd",
    "pwd",
    "cp",
    "mv",
    "rm",
    "mkdir",
    "rmdir",
    "touch",
    "man",
    "git",
    "poetry",
    # Modern alternatives to core commands
    "eza",  # modern ls alternative
    "z",  # modern cd alternative (zoxide)
    "fd",  # modern find alternative
    "bat",  # modern cat alternative
    "rg",  # modern grep alternative
    "dust",  # modern du alternative
    "duf",  # modern df alternative
    "btm",  # modern top alternative
    "procs",  # modern ps alternative
    "delta",  # modern diff alternative
    # Search and filtering
    "grep",
    "find",
    "fzf",
    "sk",
    # File inspection and manipulation
    "cat",
    "less",
    "head",
    "tail",
    "chmod",
    "chown",
    "tree",
    # System information
    "ps",
    "top",  # prefer btm
    "df",
    "du",
    "uptime",
    "uname",
    "free",
    # Network tools
    "ping",
    "curl",
    "wget",
    "ssh",
    "nc",
    "traceroute",
    "dig",
    "ifconfig",
    "scp",
    "sftp",
    # Development tools
    "vim",
    "nano",
    "jq",
    # Documentation and help
    "tldr",
    "which",
    # Compression
    "tar",
    "gzip",
    "zip",
    "unzip",
    "bzip2",
    "xz",
    # Python
    "pip",
    "pyenv",
    "virtualenv",
    "pipenv",
    "pipx",
    # Rust
    "cargo",
    # JavaScript
    "npm",
    "npx",
    "yarn",
    "fnm",
    "node",
    # Process management
    "htop",
    "kill",
    "killall",
    # Not the same on xonsh
    # "bg",
    # "fg",
    # "jobs",
    # Text processing and editing
    "awk",
    "sed",
    "sort",
    "uniq",
    "wc",
    # System monitoring and diagnostics
    "ncdu",
    "lsof",
    "strace",
    # "tmux",
    # "screen",
    "glances",
    "nmap",
    "netstat",
    # "rsync",
    # "mtr",
    # Container and virtualization
    "docker",
    "podman",
    "kubectl",
    "vagrant",
    # macOS specific
    "open",
    "pbcopy",
    "pbpaste",
    "brew",
    # Package management (Linux)
    "apt",
    "yum",
    "dnf",
    "pacman",
    # System administration
    "sudo",
    "su",
    "zsh",
    "bash",
}

DROPPED_TLDR_COMMANDS = {
    "less",  # "less" has keyboard examples, not command line
    "license",  # Confusing
    "hello",  # Confusing
}

RECOMMENDED_TLDR_COMMANDS = sorted(STANDARD_SHELL_COMMANDS - DROPPED_TLDR_COMMANDS)
