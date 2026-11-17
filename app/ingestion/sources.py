"""The list of source documents, kept in a YAML file under version control."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Source(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    company: str
    ticker: str
    year: int = Field(ge=2000, le=2100)
    title: str
    url: HttpUrl | None = None
    file: str

    @field_validator("file")
    @classmethod
    def file_is_a_plain_pdf_name(cls, value: str) -> str:
        if "/" in value or "\\" in value or not value.lower().endswith(".pdf"):
            raise ValueError("file must be a bare .pdf file name, e.g. tlv-2025.pdf")
        return value

    def path(self, data_dir: Path) -> Path:
        return data_dir / self.file


class SourceList(BaseModel):
    documents: list[Source]

    @field_validator("documents")
    @classmethod
    def ids_and_files_are_unique(cls, documents: list[Source]) -> list[Source]:
        for attr in ("id", "file"):
            values = [getattr(d, attr) for d in documents]
            duplicates = {v for v in values if values.count(v) > 1}
            if duplicates:
                raise ValueError(f"duplicate {attr}: {sorted(duplicates)}")
        return documents


def load_sources(path: Path) -> list[Source]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return SourceList.model_validate(data).documents
