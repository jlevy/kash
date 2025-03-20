# Portions of this code are from xonsh:
#
# Copyright (c) 2016, xonsh
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of lazyasd nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Based on the xonsh implementation but with Python 3 type improvements:
# https://github.com/xonsh/lazyasd/blob/main/lazyasd-py3.py
# Updated by github.com/jlevy for kash.

from collections.abc import Callable, Iterator, Mapping
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")


class LazyObject(Generic[T]):
    def __init__(self, load: Callable[[], T], ctx: Mapping[str, T], name: str):
        """
        Lazily loads an object via the load function the first time an
        attribute is accessed. Once loaded, it will replace itself in the
        provided context (typically the globals of the call site) with the
        given name.

        Parameters
        ----------
        load : Callable[[], T]
            A loader function that performs the actual object construction.
        ctx : Mapping[str, T]
            Context to replace the LazyObject instance in
            with the object returned by load().
        name : str
            Name in the context to give the loaded object. This *should*
            be the name on the LHS of the assignment.
        """
        self._lasdo: dict[str, Any] = {
            "loaded": False,
            "load": load,
            "ctx": ctx,
            "name": name,
        }

    def _lazy_obj(self) -> T:
        d = self._lasdo
        if d["loaded"]:
            return d["obj"]
        try:
            obj = d["load"]()
            d["ctx"][d["name"]] = d["obj"] = obj
            d["loaded"] = True
            return obj
        except Exception as e:
            raise e
            raise RuntimeError("Error loading object") from e

    def __getattribute__(self, name: str) -> Any:
        if name in {"_lasdo", "_lazy_obj"}:
            return super().__getattribute__(name)
        obj = self._lazy_obj()
        return getattr(obj, name)

    def __bool__(self) -> bool:
        return bool(self._lazy_obj())

    def __iter__(self) -> Iterator:
        return iter(self._lazy_obj())  # pyright: ignore

    def __getitem__(self, item: Any) -> Any:
        return self._lazy_obj()[item]  # pyright: ignore

    def __setitem__(self, key: Any, value: Any) -> None:
        self._lazy_obj()[key] = value  # pyright: ignore

    def __delitem__(self, item: Any) -> None:
        del self._lazy_obj()[item]  # pyright: ignore

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._lazy_obj()(*args, **kwargs)  # pyright: ignore

    def __lt__(self, other: Any) -> bool:
        return self._lazy_obj() < other

    def __le__(self, other: Any) -> bool:
        return self._lazy_obj() <= other

    def __eq__(self, other: Any) -> bool:
        return self._lazy_obj() == other

    def __ne__(self, other: Any) -> bool:
        return self._lazy_obj() != other

    def __gt__(self, other: Any) -> bool:
        return self._lazy_obj() > other

    def __ge__(self, other: Any) -> bool:
        return self._lazy_obj() >= other

    def __hash__(self) -> int:
        return hash(self._lazy_obj())

    def __or__(self, other: Any) -> Any:
        return self._lazy_obj() | other

    def __str__(self) -> str:
        return str(self._lazy_obj())

    def __repr__(self) -> str:
        return repr(self._lazy_obj())

    def __len__(self) -> int:
        return len(self._lazy_obj())  # pyright: ignore


def lazyobject(f: Callable[[], T]) -> T:
    """
    Decorator for constructing lazy objects from a function.

    For simplicity, we tell a white lie to the type checker that this is actually of type T.
    """
    return cast(T, LazyObject(f, f.__globals__, f.__name__))
