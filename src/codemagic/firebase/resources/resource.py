from __future__ import annotations

import re
from abc import ABC
from datetime import datetime
from typing import ClassVar
from typing import Dict
from typing import Optional


class Resource(ABC):
    __google_api_label__: ClassVar[Optional[str]] = None

    @classmethod
    def get_label(cls) -> str:
        if cls.__google_api_label__:
            return cls.__google_api_label__
        return f'{cls.__name__.lower()}s'

    def dict(self) -> Dict:
        return {k: self._serialize(v) for k, v in self.__dict__.items()}

    @classmethod
    def _serialize(cls, obj):
        if isinstance(obj, Resource):
            return obj.dict()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    @staticmethod
    def _format_attribute_name(name: str) -> str:
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        name = name.lower().capitalize()
        return re.sub(r'uri', 'URI', name, flags=re.IGNORECASE)

    def __str__(self) -> str:
        s = ''
        for attribute_name, value in self.__dict__.items():
            if value is None:
                continue
            name = self._format_attribute_name(attribute_name)
            s += f'\n{name}: {value}'
            if isinstance(value, Resource):
                s += '\n'
        return s
