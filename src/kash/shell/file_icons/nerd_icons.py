# Based on https://github.com/eza-community/eza/blob/1780411a76fe9d5f3967f3130ed1d4cdc79b493a/src/output/icons.rs
#
# Modified version license:
# SPDX-FileCopyrightText: 2025 Joshua Levy
# SPDX-License-Identifier: MIT
#
# Original version licenses:
# SPDX-FileCopyrightText: 2024 Christina Sørensen
# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: 2023-2024 Christina Sørensen, eza contributors
# SPDX-FileCopyrightText: 2014 Benjamin Sago
# SPDX-License-Identifier: MIT

# TODO: Consider using lsd icons instead?
# https://github.com/lsd-rs/lsd/blob/master/src/theme/icon.rs

import os
from dataclasses import dataclass
from enum import Enum

NBSP = "\u00a0"


@dataclass(frozen=True)
class Icon:
    icon_char: str
    name: str

    @property
    def readable(self) -> str:
        # nbsp to ensure there's space even in HTML rendering since icon is
        # typically double width.
        return f"{self.icon_char}{NBSP}{NBSP}{self.name}"


# fmt: off
class Icons(str, Enum):
    ARCHIVE = '\uf410'             # 
    AUDIO = "\uf001"               # 
    BINARY = "\ueae8"              # 
    BOOK = "\ue28b"                # 
    CALENDAR = "\ueab0"            # 
    CACHE = "\uf49b"               # 
    CAD = "\U000F0EEB"             # 󰻫   (5 hex digits => \U000F0EEB)
    CLOCK = "\uf43a"               # 
    COMPRESSED = "\uf410"          # 
    CONFIG = "\ue615"              # 
    CSS3 = "\ue749"                # 
    DATABASE = "\uf1c0"            # 
    DIFF = "\uf440"                # 
    DISK_IMAGE = "\ue271"          # 
    DOCKER = "\ue650"              # 
    DOCUMENT = "\uf1c2"            # 
    DOWNLOAD = "\U000F01DA"        # 󰇚
    EDA_SCH = "\U000F0B45"         # 󰭅
    EDA_PCB = "\ueabe"             # 
    EMACS = "\ue632"               # 
    ESLINT = "\ue655"              # 
    FILE = "\uf15b"                # 
    FILE_3D = "\U000F01A7"         # 󰆧
    FILE_OUTLINE = "\uf016"        # 
    FOLDER = "\ue5ff"              # 
    FOLDER_CONFIG = "\ue5fc"       # 
    FOLDER_GIT = "\ue5fb"          # 
    FOLDER_GITHUB = "\ue5fd"       # 
    FOLDER_HIDDEN = "\U000F179E"   # 󱞞
    FOLDER_KEY = "\U000F08AC"      # 󰢬
    FOLDER_NPM = "\ue5fa"          # 
    FOLDER_OPEN = "\uf115"         # 
    FONT = "\uf031"                # 
    FREECAD = "\uf336"             # 
    GIMP = "\uf338"                # 
    GIST_SECRET = "\ueafa"         # 
    GIT = "\uf1d3"                 # 
    GODOT = "\ue65f"               # 
    GRADLE = "\ue660"              # 
    GRAPH = "\U000F1049"           # 󱁉
    GRAPHQL = "\ue662"             # 
    GRUNT = "\ue611"               # 
    GTK = "\uf362"                 # 
    GULP = "\ue610"                # 
    HTML5 = "\uf13b"               # 
    IMAGE = "\uf1c5"               # 
    INFO = "\uf129"                # 
    INTELLIJ = "\ue7b5"            # 
    JSON = "\ue60b"                # 
    KEY = "\ueb11"                 # 
    KDENLIVE = "\uf33c"            # 
    KEYPASS = "\uf23e"             # 
    KICAD = "\uf34c"               # 
    KRITA = "\uf33d"               # 
    LANG_ARDUINO = "\uf34b"        # 
    LANG_ASSEMBLY = "\ue637"       # 
    LANG_C = "\ue61e"              # 
    LANG_CLOJURE = '\ue768'        # 
    LANG_COBOL = '\ueae7'          # 
    LANG_CPP = "\ue61d"            # 
    LANG_CSHARP = "\U000F031B"     # 󰌛
    LANG_D = "\ue7af"              # 
    LANG_ELIXIR = "\ue62d"         # 
    LANG_FENNEL = "\ue6af"         # 
    LANG_FORTRAN = "\U000F121A"    # 󱈚
    LANG_FSHARP = "\ue7a7"         # 
    LANG_GLEAM = "\U000F09A5"      # 󰦥
    LANG_GO = "\ue65e"             # 
    LANG_GROOVY = "\ue775"         # 
    LANG_HASKELL = "\ue777"        # 
    LANG_HDL = "\U000F035B"        # 󰍛
    LANG_HOLYC = "\U000F00A2"      # 󰂢
    LANG_JAVA = "\ue256"           # 
    LANG_JAVASCRIPT = "\ue74e"     # 
    LANG_KOTLIN = "\ue634"         # 
    LANG_LISP = "\uf0172"          # 󰅲
    LANG_LUA = "\ue620"            # 
    LANG_NIM = "\ue677"            # 
    LANG_OCAML = "\ue67a"          # 
    LANG_PERL = "\ue67e"           # 
    LANG_PHP = "\ue73d"            # 
    LANG_PYTHON = "\ue606"         # 
    LANG_R = "\ue68a"              # 
    LANG_RUBY = "\ue21e"           # 
    LANG_RUBYRAILS = "\ue73b"      # 
    LANG_RUST = "\ue68b"           # 
    LANG_SASS = "\ue603"           # 
    LANG_SCHEME = "\ue6b1"         # 
    LANG_STYLUS = "\ue600"         # 
    LANG_TEX = "\ue69b"            # 
    LANG_TYPESCRIPT = "\ue628"     # 
    LANG_V = "\ue6ac"              # 
    LIBRARY = "\ueb9c"             # 
    LICENSE = "\uf02d"             # 
    LOCK = "\uf023"                # 
    LOG = "\uf18d"                 # 
    MAKE = "\ue673"                # 
    MARKDOWN = "\uf48a"            # 
    MUSTACHE = "\ue60f"            # 
    NODEJS = "\ue718"              # 
    NPM = "\ue71e"                 # 
    OS_ANDROID = "\ue70e"          # 
    OS_APPLE = "\uf179"            # 
    OS_LINUX = "\uf17c"            # 
    OS_WINDOWS = "\uf17a"          # 
    OS_WINDOWS_CMD = "\uebc4"      # 
    PLAYLIST = "\U000F0CB9"        # 󰲹
    POWERSHELL = "\uebc7"          # 
    PRIVATE_KEY = "\U000F0306"     # 󰌆
    PUBLIC_KEY = "\U000F0DD6"      # 󰷖
    QT = "\uf375"                  # 
    RAZOR = "\uf1fa"               # 
    REACT = "\ue7ba"               # 
    README = "\U000F00BA"          # 󰂺
    SHEET = "\uf1c3"               # 
    SHELL = "\U000F1183"           # 󱆃
    SHELL_CMD = "\uf489"           # 
    SHIELD_CHECK = "\U000F0565"    # 󰕥
    SHIELD_KEY = "\U000F0BC4"      # 󰯄
    SHIELD_LOCK = "\U000F099D"     # 󰦝
    SIGNED_FILE = "\U000F19C3"     # 󱧃
    SLIDE = "\uf1c4"               # 
    SQLITE = "\ue7c4"              # 
    SUBLIME = "\ue7aa"             # 
    SUBTITLE = "\U000F0A16"        # 󰨖
    TERRAFORM = "\U000F1062"       # 󱁢
    TEXT = "\uf15c"                # 
    TYPST = "\uf37f"               # 
    TMUX = "\uebc8"                # 
    TOML = "\ue6b2"                # 
    TRANSLATION = "\U000F05CA"     # 󰗊
    UNITY = "\ue721"               # 
    VECTOR = "\U000F0559"          # 󰕙
    VIDEO = "\uf03d"               # 
    VIM = "\ue7c5"                 # 
    WRENCH = "\uf0ad"              # 
    XML = "\U000F05C0"             # 󰗀
    YAML = "\uee19"                #     # See https://github.com/jesseweed/seti-ui/issues/672
    YARN = "\ue6a7"                # 

    @property
    def readable_name(self) -> str:
        name = self.name
        new_suffix = ""

        if name == "FILE_OUTLINE":
            name = "File"
        for prefix, suffix in [("OS_",  " OS"), ("LANG_",  " Language"), ("FOLDER_",  " Folder")]:
            if name.startswith(prefix):
                name = name[len(prefix):]
                new_suffix = suffix
                break
            
        name = name.lower().replace("_",  " ").title() + new_suffix
        return name

    @property
    def icon(self) -> Icon:
        return Icon(self.value, self.readable_name)

# fmt: on

DIRECTORY_ICONS = {
    ".config": Icons.FOLDER_CONFIG,
    ".git": Icons.FOLDER_GIT,
    ".github": Icons.FOLDER_GITHUB,
    ".npm": Icons.FOLDER_NPM,
    ".ssh": Icons.FOLDER_KEY,
    ".Trash": "\uf1f8",  # 
    "config": Icons.FOLDER_CONFIG,
    "Contacts": "\U000f024c",  # 󰉌
    "cron.d": Icons.FOLDER_CONFIG,
    "cron.daily": Icons.FOLDER_CONFIG,
    "cron.hourly": Icons.FOLDER_CONFIG,
    "cron.minutely": Icons.FOLDER_CONFIG,
    "cron.monthly": Icons.FOLDER_CONFIG,
    "cron.weekly": Icons.FOLDER_CONFIG,
    "Desktop": "\uf108",  # 
    "Downloads": "\U000f024d",  # 󰉍
    "etc": Icons.FOLDER_CONFIG,
    "Favorites": "\U000f069d",  # 󰚝
    "hidden": Icons.FOLDER_HIDDEN,
    "home": "\U000f10b5",  # 󱂵
    "include": Icons.FOLDER_CONFIG,
    "Mail": "\U000f01f0",  # 󰇰
    "Movies": "\U000f0fce",  # 󰿎
    "Music": "\U000f1359",  # 󱍙
    "node_modules": Icons.FOLDER_NPM,
    "npm_cache": Icons.FOLDER_NPM,
    "pam.d": Icons.FOLDER_KEY,
    "Pictures": "\U000f024f",  # 󰉏
    "ssh": Icons.FOLDER_KEY,
    "sudoers.d": Icons.FOLDER_KEY,
    "Videos": "\uf03d",  # 
    "xbps.d": Icons.FOLDER_CONFIG,
    "xorg.conf.d": Icons.FOLDER_CONFIG,
    "hi": Icons.BINARY,  # 
    "cabal": Icons.LANG_HASKELL,  # 
}


FILENAME_ICONS = {
    ".aliases": Icons.SHELL,
    ".atom": "\ue764",  # 
    ".bashrc": Icons.SHELL,
    ".bash_aliases": Icons.SHELL,
    ".bash_history": Icons.SHELL,
    ".bash_logout": Icons.SHELL,
    ".bash_profile": Icons.SHELL,
    ".CFUserTextEncoding": Icons.OS_APPLE,
    ".clang-format": Icons.CONFIG,
    ".clang-tidy": Icons.CONFIG,
    ".codespellrc": "\U000f04c6",  # 󰓆
    ".condarc": "\ue715",  # 
    ".cshrc": Icons.SHELL,
    ".DS_Store": Icons.OS_APPLE,
    ".editorconfig": "\ue652",  # 
    ".emacs": Icons.EMACS,
    ".envrc": "\uf462",  # 
    ".eslintrc.cjs": Icons.ESLINT,
    ".eslintrc.js": Icons.ESLINT,
    ".eslintrc.json": Icons.ESLINT,
    ".eslintrc.yaml": Icons.ESLINT,
    ".eslintrc.yml": Icons.ESLINT,
    ".fennelrc": Icons.CONFIG,
    ".gitattributes": Icons.GIT,
    ".git-blame-ignore-revs": Icons.GIT,
    ".gitconfig": Icons.GIT,
    ".gitignore": Icons.GIT,
    ".gitignore_global": Icons.GIT,
    ".gitlab-ci.yml": "\uf296",  # 
    ".gitmodules": Icons.GIT,
    ".gtkrc-2.0": Icons.GTK,
    ".htaccess": Icons.CONFIG,
    ".htpasswd": Icons.CONFIG,
    ".idea": Icons.INTELLIJ,
    ".ideavimrc": Icons.VIM,
    ".inputrc": Icons.CONFIG,
    ".kshrc": Icons.SHELL,
    ".login": Icons.SHELL,
    ".logout": Icons.SHELL,
    ".luacheckrc": Icons.CONFIG,
    ".luaurc": Icons.CONFIG,
    ".nanorc": "\ue838",  # 
    ".nuxtrc": "\U000f1106",  # 󱄆
    ".mailmap": Icons.GIT,
    ".node_repl_history": Icons.NODEJS,
    ".npmignore": Icons.NPM,
    ".npmrc": Icons.NPM,
    ".pre-commit-config.yaml": "\U000f06e2",  # 󰛢
    ".prettierrc": "\ue6b4",  # 
    ".parentlock": Icons.LOCK,
    ".profile": Icons.SHELL,
    ".pylintrc": Icons.CONFIG,
    ".python_history": Icons.LANG_PYTHON,
    ".rustfmt.toml": Icons.LANG_RUST,
    ".rvm": Icons.LANG_RUBY,
    ".rvmrc": Icons.LANG_RUBY,
    ".SRCINFO": "\uf303",  # 
    ".tcshrc": Icons.SHELL,
    ".viminfo": Icons.VIM,
    ".vimrc": Icons.VIM,
    ".Xauthority": Icons.CONFIG,
    ".xinitrc": Icons.CONFIG,
    ".Xresources": Icons.CONFIG,
    ".yarnrc": Icons.YARN,
    ".zlogin": Icons.SHELL,
    ".zlogout": Icons.SHELL,
    ".zprofile": Icons.SHELL,
    ".zshenv": Icons.SHELL,
    ".zshrc": Icons.SHELL,
    ".zsh_history": Icons.SHELL,
    ".zsh_sessions": Icons.SHELL,
    "._DS_Store": Icons.OS_APPLE,
    "a.out": Icons.SHELL_CMD,
    "authorized_keys": "\U000f08c0",  # 󰣀
    "AUTHORS": "\uedca",  # 
    "AUTHORS.txt": "\uedca",  # 
    "bashrc": Icons.SHELL,
    "brewfile": "\U000f1116",  # 󱄖
    "brewfile.lock.json": "\U000f1116",
    "bspwmrc": "\uf355",  # 
    "build.gradle.kts": Icons.GRADLE,
    "build.zig.zon": "\ue6a9",  # 
    "bun.lockb": "\ue76f",  # 
    "cantorrc": "\uf373",  # 
    "Cargo.lock": Icons.LANG_RUST,
    "Cargo.toml": Icons.LANG_RUST,
    "CMakeLists.txt": "\ue794",  # 
    "CODE_OF_CONDUCT": "\uf4ae",  # 
    "CODE_OF_CONDUCT.md": "\uf4ae",
    "composer.json": Icons.LANG_PHP,
    "composer.lock": Icons.LANG_PHP,
    "config": Icons.CONFIG,
    "config.status": Icons.CONFIG,
    "configure": Icons.WRENCH,
    "configure.ac": Icons.CONFIG,
    "configure.in": Icons.CONFIG,
    "constraints.txt": Icons.LANG_PYTHON,
    "COPYING": Icons.LICENSE,
    "COPYRIGHT": Icons.LICENSE,
    "crontab": Icons.CONFIG,
    "crypttab": Icons.CONFIG,
    "csh.cshrc": Icons.SHELL,
    "csh.login": Icons.SHELL,
    "csh.logout": Icons.SHELL,
    "docker-compose.yml": Icons.DOCKER,
    "Dockerfile": Icons.DOCKER,
    "compose.yaml": Icons.DOCKER,
    "compose.yml": Icons.DOCKER,
    "docker-compose.yaml": Icons.DOCKER,
    "dune": Icons.LANG_OCAML,
    "dune-project": Icons.WRENCH,
    "Earthfile": "\uf0ac",  # 
    "COMMIT_EDITMSG": Icons.GIT,  # (for .git commit msg)
    "environment": Icons.CONFIG,
    "favicon.ico": "\ue623",  # 
    "fonts.conf": Icons.FONT,
    "fp-info-cache": Icons.KICAD,
    "fp-lib-table": Icons.KICAD,
    "FreeCAD.conf": Icons.FREECAD,
    "GNUmakefile": Icons.MAKE,
    "go.mod": Icons.LANG_GO,
    "go.sum": Icons.LANG_GO,
    "go.work": Icons.LANG_GO,
    "gradle": Icons.GRADLE,
    "gradle.properties": Icons.GRADLE,
    "gradlew": Icons.GRADLE,
    "gradlew.bat": Icons.GRADLE,
    "group": Icons.LOCK,
    "gruntfile.coffee": Icons.GRUNT,
    "gruntfile.js": Icons.GRUNT,
    "gruntfile.ls": Icons.GRUNT,
    "gshadow": Icons.LOCK,
    "gtkrc": Icons.GTK,
    "gulpfile.coffee": Icons.GULP,
    "gulpfile.js": Icons.GULP,
    "gulpfile.ls": Icons.GULP,
    "heroku.yml": "\ue77b",  # 
    "hostname": Icons.CONFIG,
    "hypridle.conf": "\uf359",  # 
    "hyprland.conf": "\uf359",
    "hyprlock.conf": "\uf359",
    "hyprpaper.conf": "\uf359",
    "i3blocks.conf": "\uf35a",  # 
    "i3status.conf": "\uf35a",
    "id_dsa": Icons.PRIVATE_KEY,
    "id_ecdsa": Icons.PRIVATE_KEY,
    "id_ecdsa_sk": Icons.PRIVATE_KEY,
    "id_ed25519": Icons.PRIVATE_KEY,
    "id_ed25519_sk": Icons.PRIVATE_KEY,
    "id_rsa": Icons.PRIVATE_KEY,
    "index.theme": "\uee72",  # 
    "inputrc": Icons.CONFIG,
    "Jenkinsfile": "\ue66e",  # 
    "jsconfig.json": Icons.LANG_JAVASCRIPT,
    "Justfile": Icons.WRENCH,
    "justfile": Icons.WRENCH,
    "kalgebrarc": "\uf373",  # 
    "kdeglobals": "\uf373",
    "kdenlive-layoutsrc": Icons.KDENLIVE,
    "kdenliverc": Icons.KDENLIVE,
    "known_hosts": "\U000f08c0",  # 󰣀
    "kritadisplayrc": Icons.KRITA,
    "kritarc": Icons.KRITA,
    "LICENCE": Icons.LICENSE,
    "LICENCE.md": Icons.LICENSE,
    "LICENCE.txt": Icons.LICENSE,
    "LICENSE": Icons.LICENSE,
    "LICENSE-APACHE": Icons.LICENSE,
    "LICENSE-MIT": Icons.LICENSE,
    "LICENSE.md": Icons.LICENSE,
    "LICENSE.txt": Icons.LICENSE,
    "localized": Icons.OS_APPLE,
    "localtime": Icons.CLOCK,
    "lock": Icons.LOCK,
    "LOCK": Icons.LOCK,
    "log": Icons.LOG,
    "LOG": Icons.LOG,
    "lxde-rc.xml": "\uf363",  # 
    "lxqt.conf": "\uf364",  # 
    "Makefile": Icons.MAKE,
    "makefile": Icons.MAKE,
    "Makefile.ac": Icons.MAKE,
    "Makefile.am": Icons.MAKE,
    "Makefile.in": Icons.MAKE,
    "MANIFEST": Icons.LANG_PYTHON,
    "MANIFEST.in": Icons.LANG_PYTHON,
    "mpv.conf": "\uf36e",  # 
    "npm-shrinkwrap.json": Icons.NPM,
    "npmrc": Icons.NPM,
    "package-lock.json": Icons.NPM,
    "package.json": Icons.NPM,
    "passwd": Icons.LOCK,
    "php.ini": Icons.LANG_PHP,
    "PKGBUILD": "\uf303",  # 
    "platformio.ini": "\ue682",  # 
    "pom.xml": "\ue674",  # 
    "Procfile": "\ue77b",  # 
    "profile": Icons.SHELL,
    "PrusaSlicer.ini": "\uf351",  # 
    "PrusaSlicerGcodeViewer.ini": "\uf351",
    "pyvenv.cfg": Icons.LANG_PYTHON,
    "pyproject.toml": Icons.LANG_PYTHON,
    "qt5ct.conf": Icons.QT,
    "qt6ct.conf": Icons.QT,
    "QtProject.conf": Icons.QT,
    "Rakefile": Icons.LANG_RUBY,
    "README": Icons.README,
    "README.md": Icons.README,
    "release.toml": Icons.LANG_RUST,
    "requirements.txt": Icons.LANG_PYTHON,
    "robots.txt": "\U000f06a9",  # 󰚩
    "rubydoc": Icons.LANG_RUBYRAILS,
    "rvmrc": Icons.LANG_RUBY,
    "SECURITY": "\U000f0483",  # 󰒃
    "SECURITY.md": "\U000f0483",
    "settings.gradle.kts": Icons.GRADLE,
    "shadow": Icons.LOCK,
    "shells": Icons.CONFIG,
    "sudoers": Icons.LOCK,
    "sxhkdrc": Icons.CONFIG,
    "sym-lib-table": Icons.KICAD,
    "timezone": Icons.CLOCK,
    "tmux.conf": Icons.TMUX,
    "tmux.conf.local": Icons.TMUX,
    "tsconfig.json": Icons.LANG_TYPESCRIPT,
    "Vagrantfile": "\u2371",  # ⍱
    "vlcrc": "\U000f057c",  # 󰕼
    "webpack.config.js": "\U000f072b",  # 󰜫
    "weston.ini": "\uf367",  # 
    "xmobarrc": "\uf35e",  # 
    "xmobarrc.hs": "\uf35e",
    "xmonad.hs": "\uf35e",
    "yarn.lock": Icons.YARN,
    "zlogin": Icons.SHELL,
    "zlogout": Icons.SHELL,
    "zprofile": Icons.SHELL,
    "zshenv": Icons.SHELL,
    "zshrc": Icons.SHELL,
}


# fmt: off

EXTENSION_ICONS = {
    "123dx": Icons.CAD,              # 󰻫
    "3dm": Icons.CAD,                # 󰻫
    "3g2": Icons.VIDEO,              # 
    "3gp": Icons.VIDEO,              # 
    "3gp2": Icons.VIDEO,             # 
    "3gpp": Icons.VIDEO,             # 
    "3gpp2": Icons.VIDEO,            # 
    "3mf": Icons.FILE_3D,            # 󰆧
    "7z": Icons.COMPRESSED,          # 
    "a": Icons.OS_LINUX,             # 
    "aac": Icons.AUDIO,              # 
    "acf": "\uf1b6",                  # 
    "age": Icons.SHIELD_LOCK,        # 󰦝
    "ai": "\ue7b4",                  # 
    "aif": Icons.AUDIO,              # 
    "aifc": Icons.AUDIO,             # 
    "aiff": Icons.AUDIO,             # 
    "alac": Icons.AUDIO,             # 
    "android": Icons.OS_ANDROID,     # 
    "ape": Icons.AUDIO,              # 
    "apk": Icons.OS_ANDROID,         # 
    "apng": Icons.IMAGE,             # 
    "app": Icons.FILE,               # 
    "ar": Icons.OS_LINUX,            # 
    "arff": Icons.DATABASE,          # 
    "as": "\ue60b",                  # 
    "asm": Icons.LANG_ASSEMBLY,      # 
    "asp": Icons.LANG_PHP,           # 
    "aspx": Icons.LANG_PHP,          # 
    "atom": "\ue764",                # 
    "aup": Icons.AUDIO,              # 
    "aux": Icons.LANG_TEX,           # 
    "avif": Icons.IMAGE,             # 
    "avi": Icons.VIDEO,              # 
    "awk": Icons.SHELL_CMD,          # 
    "axlsx": Icons.SHEET,            # 
    "azw": Icons.BOOK,               # 
    "azw3": Icons.BOOK,              # 
    "b": Icons.LANG_ASSEMBLY,        # 
    "bash": Icons.SHELL_CMD,         # 
    "bash_history": Icons.SHELL,     # 󱆃
    "bash_profile": Icons.SHELL,     # 󱆃
    "bashrc": Icons.SHELL,           # 󱆃
    "bat": Icons.OS_WINDOWS_CMD,     # 
    "bats": Icons.SHELL_CMD,         # 
    "bb": Icons.LANG_CLOJURE,        # 
    "bbx": Icons.LANG_TEX,           # 
    "bdf": Icons.FONT,               # 
    "bib": Icons.LANG_TEX,           # 
    "bin": Icons.BINARY,             # 
    "bmp": Icons.IMAGE,              # 
    "bs": Icons.LANG_ASSEMBLY,       # 
    "bz2": Icons.COMPRESSED,         # 
    "c": Icons.LANG_C,               # 
    "c++": Icons.LANG_CPP,           # 
    "cab": Icons.COMPRESSED,         # 
    "cabal": Icons.LANG_HASKELL,     # 
    "caj": Icons.BOOK,               # 
    "cal": Icons.CALENDAR,           # 
    "capnp": Icons.LANG_C,           # 
    "cat": Icons.TEXT,               # 
    "cb7": Icons.ARCHIVE,            # 
    "cbl": Icons.LANG_COBOL,         # 
    "cbr": Icons.ARCHIVE,            # 
    "cbt": Icons.ARCHIVE,            # 
    "cbz": Icons.ARCHIVE,            # 
    "cc": Icons.LANG_CPP,            # 
    "ccp": Icons.LANG_CPP,           # 
    "cct": Icons.LANG_CPP,           # 
    "cdf": Icons.DATABASE,           # 
    "cer": Icons.SHIELD_CHECK,       # 󰕥
    "cfg": Icons.CONFIG,             # 
    "cgm": Icons.IMAGE,              # 
    "chs": Icons.LANG_HASKELL,       # 
    "class": Icons.LANG_JAVA,        # 
    "clj": Icons.LANG_CLOJURE,       # 
    "cljc": Icons.LANG_CLOJURE,      # 
    "cljs": Icons.LANG_CLOJURE,      # 
    "cls": Icons.LANG_TEX,           # 
    "cmake": "\ue3ed",               # 
    "coffee": "\ue751",              # 
    "conf": Icons.CONFIG,            # 
    "cp": Icons.LANG_CPP,            # 
    "cpp": Icons.LANG_CPP,           # 
    "cpy": Icons.LANG_PYTHON,        # 
    "cr": "\ue739",                  # 
    "cs": Icons.LANG_CSHARP,         # 󰌛
    "csh": Icons.SHELL_CMD,          # 
    "cson": Icons.JSON,              # 
    "css": Icons.CSS3,               # 
    "csv": Icons.SHEET,              # 
    "cue": Icons.AUDIO,              # 
    "cvs": Icons.DATABASE,           # 
    "cxx": Icons.LANG_CPP,           # 
    "d": Icons.LANG_D,               # 
    "dart": "\ue798",                # 
    "db": Icons.DATABASE,            # 
    "deb": "\ue77d",                 # 
    "diff": Icons.DIFF,              # 
    "dll": Icons.OS_WINDOWS,         # 
    "doc": Icons.DOCUMENT,           # 
    "docx": Icons.DOCUMENT,          # 
    "dot": Icons.GRAPH,              # 󱁉
    "dump": Icons.DATABASE,          # 
    "end": Icons.LANG_CLOJURE,       # 
    "eex": Icons.LANG_ELIXIR,        # 
    "efi": Icons.DISK_IMAGE,         # 
    "ejs": "\ue618",                 # 
    "el": Icons.LANG_LISP,           # 󰅲
    "elm": "\ue62c",                 # 
    "eot": Icons.FONT,               # 
    "eps": Icons.VECTOR,             # 󰕙
    "epub": Icons.BOOK,              # 
    "erl": "\ue7b1",                 # 
    "ex": Icons.LANG_ELIXIR,         # 
    "exe": Icons.OS_WINDOWS,         # 
    "exs": Icons.LANG_ELIXIR,        # 
    "f#": Icons.LANG_FSHARP,         # 
    "f90": Icons.LANG_FORTRAN,       # 󱈚
    "fish": Icons.SHELL_CMD,         # 
    "flac": Icons.AUDIO,             # 
    "flv": Icons.VIDEO,              # 
    "fs": Icons.LANG_FSHARP,         # 
    "fsi": Icons.LANG_FSHARP,        # 
    "fsscript": Icons.LANG_FSHARP,   # 
    "fsx": Icons.LANG_FSHARP,        # 
    "gadget": Icons.LANG_CSHARP,     # 󰌛
    "gam": Icons.LANG_FSHARP,        # 
    "gba": "\uf1393",                # 󱎓
    "gbl": Icons.EDA_PCB,            # 
    "gbo": Icons.EDA_PCB,            # 
    "gbp": Icons.EDA_PCB,            # 
    "gbr": Icons.EDA_PCB,            # 
    "gbs": Icons.EDA_PCB,            # 
    "gcode": "\uf0af4",              # 󰫴
    "gd": Icons.GODOT,               # 
    "gdoc": Icons.DOCUMENT,          # 
    "gem": Icons.LANG_RUBY,          # 
    "gemfile": Icons.LANG_RUBY,      # 
    "gemspec": Icons.LANG_RUBY,      # 
    "gform": "\uf298",               # 
    "gif": Icons.IMAGE,              # 
    "git": Icons.GIT,                # 
    "gleam": Icons.LANG_GLEAM,       # 󰦥
    "gm1": Icons.EDA_PCB,            # 
    "gml": Icons.EDA_PCB,            # 
    "go": Icons.LANG_GO,             # 
    "godot": Icons.GODOT,            # 
    "gpg": Icons.SHIELD_LOCK,        # 󰦝
    "gql": Icons.GRAPHQL,            # 
    "gradle": Icons.GRADLE,          # 
    "graphql": Icons.GRAPHQL,        # 
    "gresource": Icons.GTK,          # 
    "groovy": Icons.LANG_GROOVY,     # 
    "gsheet": Icons.SHEET,           # 
    "gslides": Icons.SLIDE,          # 
    "gtl": Icons.EDA_PCB,            # 
    "gto": Icons.EDA_PCB,            # 
    "gtp": Icons.EDA_PCB,            # 
    "gts": Icons.EDA_PCB,            # 
    "guardfile": Icons.LANG_RUBY,    # 
    "gv": Icons.GRAPH,               # 󱁉
    "gvy": Icons.LANG_GROOVY,        # 
    "gz": Icons.COMPRESSED,          # 
    "h": Icons.LANG_C,               # 
    "h++": Icons.LANG_CPP,           # 
    "h264": Icons.VIDEO,             # 
    "haml": "\ue664",                # 
    "hbs": Icons.MUSTACHE,           # 
    "hc": Icons.LANG_HOLYC,          # 󰂢
    "heic": Icons.IMAGE,             # 
    "heics": Icons.VIDEO,            # 
    "heif": Icons.IMAGE,             # 
    "hex": "\uf12a7",                # 󱊧
    "hh": Icons.LANG_CPP,            # 
    "hpp": Icons.LANG_CPP,           # 
    "hs": Icons.LANG_HASKELL,        # 
    "htm": Icons.HTML5,              # 
    "html": Icons.HTML5,             # 
    "hxx": Icons.LANG_CPP,           # 
    "iam": Icons.CAD,                # 󰻫
    "ical": Icons.CALENDAR,          # 
    "icalendar": Icons.CALENDAR,     # 
    "ico": Icons.IMAGE,              # 
    "ics": Icons.CALENDAR,           # 
    "ifb": Icons.CALENDAR,           # 
    "ifc": Icons.CAD,                # 󰻫
    "ige": Icons.CAD,                # 󰻫
    "iges": Icons.CAD,               # 󰻫
    "igs": Icons.CAD,                # 󰻫
    "image": Icons.DISK_IMAGE,       # 
    "img": Icons.DISK_IMAGE,         # 
    "iml": Icons.INTELLIJ,           # 
    "info": Icons.INFO,              # 
    "ini": Icons.CONFIG,             # 
    "inl": Icons.LANG_C,             # 
    "ipynb": "\ue80f",               # 
    "ino": Icons.LANG_ARDUINO,       # 
    "ipt": Icons.CAD,                # 󰻫
    "iso": Icons.DISK_IMAGE,         # 
    "j2c": Icons.IMAGE,              # 
    "j2k": Icons.IMAGE,              # 
    "jad": Icons.LANG_JAVA,          # 
    "jar": Icons.LANG_JAVA,          # 
    "java": Icons.LANG_JAVA,         # 
    "jfi": Icons.IMAGE,              # 
    "jfif": Icons.IMAGE,             # 
    "jif": Icons.IMAGE,              # 
    "jl": "\ue624",                  # 
    "jmd": Icons.MARKDOWN,           # 
    "jp2": Icons.IMAGE,              # 
    "jpe": Icons.IMAGE,              # 
    "jpeg": Icons.IMAGE,             # 
    "jpf": Icons.IMAGE,              # 
    "jpg": Icons.IMAGE,              # 
    "jpx": Icons.IMAGE,              # 
    "js": Icons.LANG_JAVASCRIPT,     # 
    "json": Icons.JSON,              # 
    "json5": Icons.JSON,             # 
    "jsonc": Icons.JSON,             # 
    "jsx": Icons.REACT,              # 
    "jxl": Icons.IMAGE,              # 
    "kbx": Icons.SHIELD_KEY,         # 󰯄
    "kdb": Icons.KEYPASS,            # 
    "kdbx": Icons.KEYPASS,           # 
    "kdenlive": Icons.KDENLIVE,      # 
    "kdenlivetitle": Icons.KDENLIVE, # 
    "key": Icons.KEY,                # 
    "kicad_dru": Icons.KICAD,        # 
    "kicad_mod": Icons.KICAD,        # 
    "kicad_pcb": Icons.KICAD,        # 
    "kicad_prl": Icons.KICAD,        # 
    "kicad_pro": Icons.KICAD,        # 
    "kicad_sch": Icons.KICAD,        # 
    "kicad_sym": Icons.KICAD,        # 
    "kicad_wks": Icons.KICAD,        # 
    "ko": Icons.OS_LINUX,            # 
    "kpp": Icons.KRITA,              # 
    "kra": Icons.KRITA,              # 
    "krz": Icons.KRITA,              # 
    "ksh": Icons.SHELL_CMD,          # 
    "kt": Icons.LANG_KOTLIN,         # 
    "kts": Icons.LANG_KOTLIN,        # 
    "latex": Icons.LANG_TEX,         # 
    "lbr": Icons.LIBRARY,            # 
    "lck": Icons.LOCK,               # 
    "ldb": Icons.DATABASE,           # 
    "less": "\ue758",                # 
    "lff": Icons.FONT,               # 
    "lhs": Icons.LANG_HASKELL,       # 
    "lib": Icons.LIBRARY,            # 
    "license": Icons.LICENSE,        # 
    "lisp": "\uf0172",               # 󰅲
    "lock": Icons.LOCK,              # 
    "log": Icons.LOG,                # 
    "lpp": Icons.EDA_PCB,            # 
    "lrc": Icons.SUBTITLE,           # 󰨖
    "ltx": Icons.LANG_TEX,           # 
    "lua": Icons.LANG_LUA,           # 
    "luac": Icons.LANG_LUA,          # 
    "luau": Icons.LANG_LUA,          # 
    "lz": Icons.COMPRESSED,          # 
    "lz4": Icons.COMPRESSED,         # 
    "lzh": Icons.COMPRESSED,         # 
    "lzma": Icons.COMPRESSED,        # 
    "lzo": Icons.COMPRESSED,         # 
    "m": Icons.LANG_C,               # 
    "m2ts": Icons.VIDEO,             # 
    "m2v": Icons.VIDEO,              # 
    "m3u": Icons.PLAYLIST,           # 󰲹
    "m3u8": Icons.PLAYLIST,          # 󰲹
    "m4a": Icons.AUDIO,              # 
    "m4v": Icons.VIDEO,              # 
    "magnet": "\uf076",              # 
    "md": Icons.MARKDOWN,            # 
    "mdx": Icons.MARKDOWN,           # 
    "md5": Icons.SHIELD_CHECK,       # 󰕥
    "mid": "\uf08f2",                # 󰣲
    "mjs": Icons.LANG_JAVASCRIPT,    # 
    "mk": Icons.MAKE,                # 
    "mka": Icons.AUDIO,              # 
    "mkd": Icons.MARKDOWN,           # 
    "mkv": Icons.VIDEO,              # 
    "ml": Icons.LANG_OCAML,          # 
    "mli": Icons.LANG_OCAML,         # 
    "mll": Icons.LANG_OCAML,         # 
    "mly": Icons.LANG_OCAML,         # 
    "mm": Icons.LANG_CPP,            # 
    "mobi": Icons.BOOK,              # 
    "mov": Icons.VIDEO,              # 
    "mp2": Icons.AUDIO,              # 
    "mp3": Icons.AUDIO,              # 
    "mp4": Icons.VIDEO,              # 
    "mpeg": Icons.VIDEO,             # 
    "mpg": Icons.VIDEO,              # 
    "msi": Icons.OS_WINDOWS,         # 
    "mustache": Icons.MUSTACHE,      # 
    "nix": "\uf313",                 # 
    "node": Icons.NODEJS,            # 
    "norg": "\ue847",                # 
    "o": Icons.BINARY,               # 
    "obj": Icons.FILE_3D,            # 󰆧
    "odp": "\uf37a",                 # 
    "ods": "\uf378",                 # 
    "odt": "\uf37c",                 # 
    "ogg": Icons.AUDIO,              # 
    "ogv": Icons.VIDEO,              # 
    "opus": Icons.AUDIO,             # 
    "otf": Icons.FONT,               # 
    "part": Icons.DOWNLOAD,          # 󰇚
    "patch": Icons.DIFF,             # 
    "pdf": "\uf1c1",                 # 
    "pem": Icons.KEY,                # 
    "pgm": Icons.IMAGE,              # 
    "pkg": "\ueb29",                 # 
    "pl": Icons.LANG_PERL,           # 
    "pls": Icons.PLAYLIST,           # 󰲹
    "plx": Icons.LANG_PERL,          # 
    "pm": Icons.LANG_PERL,           # 
    "png": Icons.IMAGE,              # 
    "po": Icons.TRANSLATION,         # 󰗊
    "pp": "\ue631",                  # 
    "pps": Icons.SLIDE,              # 
    "ppsx": Icons.SLIDE,             # 
    "ppt": Icons.SLIDE,              # 
    "pptx": Icons.SLIDE,             # 
    "ps": Icons.VECTOR,              # 󰕙
    "ps1": Icons.POWERSHELL,         # 
    "psd": "\ue7b8",                 # 
    "pub": Icons.PUBLIC_KEY,         # 󰷖
    "py": Icons.LANG_PYTHON,         # 
    "pyc": Icons.LANG_PYTHON,        # 
    "pyd": Icons.LANG_PYTHON,        # 
    "pyo": Icons.LANG_PYTHON,        # 
    "pyw": Icons.LANG_PYTHON,        # 
    "r": Icons.LANG_R,               # 
    "rake": Icons.LANG_RUBYRAILS,    # 
    "rar": Icons.COMPRESSED,         # 
    "rb": Icons.LANG_RUBY,           # 
    "rdata": Icons.LANG_R,           # 
    "rdb": "\ue76d",                 # 
    "rdoc": Icons.MARKDOWN,          # 
    "rds": Icons.LANG_R,             # 
    "readme": Icons.README,          # 󰂺
    "rkt": Icons.LANG_SCHEME,        # 
    "rlib": Icons.LANG_RUST,         # 
    "rmd": Icons.MARKDOWN,           # 
    "rs": Icons.LANG_RUST,           # 
    "rss": "\uf09e",                 # 
    "rtf": Icons.TEXT,               # 
    "sass": Icons.LANG_SASS,         # 
    "scala": "\ue737",               # 
    "scss": Icons.LANG_SASS,         # 
    "sh": Icons.SHELL_CMD,           # 
    "sha1": Icons.SHIELD_CHECK,      # 󰕥
    "sha256": Icons.SHIELD_CHECK,    # 󰕥
    "slim": Icons.LANG_RUBYRAILS,    # 
    "sln": "\ue70c",                 # 
    "so": Icons.OS_LINUX,            # 
    "sql": Icons.DATABASE,           # 
    "sqlite": Icons.SQLITE,          # 
    "sqlite3": Icons.SQLITE,         # 
    "styl": Icons.LANG_STYLUS,       # 
    "stylus": Icons.LANG_STYLUS,     # 
    "sublime": Icons.SUBLIME,        # 
    "svg": Icons.VECTOR,             # 󰕙
    "swift": "\ue755",               # 
    "tar": Icons.COMPRESSED,         # 
    "taz": Icons.COMPRESSED,         # 
    "tcl": "\uf06d3",                # 󰛓
    "tex": Icons.LANG_TEX,           # 
    "tf": Icons.TERRAFORM,           # 󱁢
    "toml": Icons.TOML,              # 
    "ts": Icons.LANG_TYPESCRIPT,     # 
    "tsv": Icons.SHEET,              # 
    "tsx": Icons.REACT,              # 
    "ttc": Icons.FONT,               # 
    "ttf": Icons.FONT,               # 
    "twig": "\ue61c",                # 
    "txt": Icons.TEXT,               # 
    "v": Icons.LANG_V,               # 
    "va": Icons.LANG_HDL,            # 󰍛
    "vba": Icons.FILE_3D,            # 󰆧
    "vbs": Icons.OS_WINDOWS_CMD,     # 
    "vh": Icons.LANG_HDL,            # 󰍛
    "vhd": Icons.LANG_HDL,           # 󰍛
    "vhdl": Icons.LANG_HDL,          # 󰍛
    "vim": Icons.VIM,                # 
    "vue": "\uf0844",                # 󰡄
    "wav": Icons.AUDIO,              # 
    "webm": Icons.VIDEO,             # 
    "webp": Icons.IMAGE,             # 
    "windows": Icons.OS_WINDOWS,     # 
    "wma": Icons.AUDIO,              # 
    "wmv": Icons.VIDEO,              # 
    "woff": Icons.FONT,              # 
    "woff2": Icons.FONT,             # 
    "xaml": "\uf0673",               # 󰙳
    "xcf": Icons.GIMP,               # 
    "xhtml": Icons.HTML5,            # 
    "xls": Icons.SHEET,              # 
    "xlsm": Icons.SHEET,             # 
    "xlsx": Icons.SHEET,             # 
    "xml": Icons.XML,                # 󰗀
    "xz": Icons.COMPRESSED,          # 
    "yaml": Icons.YAML,              # 
    "yml": Icons.YAML,               # 
    "zip": Icons.COMPRESSED,         # 
    "zsh": Icons.SHELL_CMD,          # 
    "zst": Icons.COMPRESSED,         # 
    "zstd": Icons.COMPRESSED,        # 
}


# fmt: on


def icon_for_file(filename: str, is_dir: bool = False, is_empty_dir: bool = False) -> Icon:
    """
    Return the Icon for a given filename, directory or not,
    following the same fallback logic as the original Rust code:
      1) If directory, check `DIRECTORY_ICONS` by full name.
         - If not found, use FOLDER_OPEN if empty, otherwise FOLDER.
      2) If not directory, check `FILENAME_ICONS` by full exact name.
      3) If that fails, check the extension (lowercased) in `EXTENSION_ICONS`.
      4) If no match at all, use FILE_OUTLINE (generic file icon).
    """
    if is_dir:
        # Check directory icons by the exact full name
        if filename in DIRECTORY_ICONS:
            icon = DIRECTORY_ICONS[filename]
            if isinstance(icon, Icons):
                return icon.icon
            else:
                return Icon(icon, filename)
        else:
            # fallback: open vs. closed folder
            if is_empty_dir:
                return Icons.FOLDER_OPEN.icon
            else:
                return Icons.FOLDER.icon
    else:
        # Check special filenames first
        if filename in FILENAME_ICONS:
            icon = FILENAME_ICONS[filename]
            if isinstance(icon, Icons):
                return icon.icon
            else:
                return Icon(icon, filename)

        # Then check file extension
        _, dot_ext = os.path.splitext(filename)
        ext = dot_ext.lower().lstrip(".")
        if ext in EXTENSION_ICONS:
            icon = EXTENSION_ICONS[ext]
            if isinstance(icon, Icons):
                return icon.icon
            else:
                return Icon(icon, ext)

        # Last fallback
        return Icons.FILE_OUTLINE.icon
