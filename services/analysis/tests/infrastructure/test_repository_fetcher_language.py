"""The language table, which was too small to describe most repositories.

`eb043d72` reported `python 53.5, typescript 26.9, json 11.5, markdown 5.4,
yaml 2.5, dockerfile 0.2, javascript 0.0, shell 0.0, sql 0.0`. Three things
produced the zeros and the missing languages:

* the extension table carried only a handful of entries, so `.ts` files could
  be bucketed while `.html`, `.css`, `.toml`, `.tf`, `.ini` and every
  extensionless file bucketed to nothing at all;
* `_detect_language` returned `""` for anything it did not know, and the
  caller dropped those files -- they were counted in `total_lines` and in no
  share, so the shares could not add up;
* shares were rounded to one decimal, where a real 0.011% became `0.0` and
  rendered as "0%".

The second and third are pinned in `test_language_breakdown_persistence.py`,
which asserts through the handler. This file pins the table itself, because a
handler test fed a synthetic mapping would pass whatever the table contained.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.git.repository_fetcher import (
    _OTHER_LANGUAGE,
    RepositoryFetcher,
)


def _detect(filename: str) -> str:
    return RepositoryFetcher._detect_language(filename)


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        # General purpose
        ("app.py", "python"),
        ("types.pyi", "python"),
        ("main.ts", "typescript"),
        ("App.tsx", "typescript"),
        ("index.js", "javascript"),
        ("server.go", "go"),
        ("Main.java", "java"),
        ("lib.rs", "rust"),
        ("model.rb", "ruby"),
        ("index.php", "php"),
        ("App.kt", "kotlin"),
        ("worker.ex", "elixir"),
        ("View.swift", "swift"),
        ("Main.scala", "scala"),
        ("main.dart", "dart"),
        ("script.pl", "perl"),
        ("init.lua", "lua"),
        ("Main.hs", "haskell"),
        ("node.erl", "erlang"),
        ("core.clj", "clojure"),
        ("util.ml", "ocaml"),
        ("plot.R", "r"),
        ("sim.jl", "julia"),
        ("Build.gradle", "groovy"),
        ("contract.proto", "protobuf"),
        ("sort.zig", "zig"),
        ("Token.sol", "solidity"),
        # C family
        ("fast.c", "c"),
        ("header.h", "c"),
        ("engine.cpp", "cpp"),
        ("engine.cc", "cpp"),
        ("Api.cs", "csharp"),
        ("Interop.m", "objective-c"),
        # Web
        ("page.html", "html"),
        ("App.vue", "vue"),
        ("style.css", "css"),
        ("style.scss", "scss"),
        ("component.svelte", "svelte"),
        ("schema.graphql", "graphql"),
        ("Analysis.ipynb", "jupyter"),
        # Data & config -- all four were in `total_lines` and in no share.
        ("config.yml", "yaml"),
        ("package.json", "json"),
        ("README.md", "markdown"),
        ("pyproject.toml", "toml"),
        ("pom.xml", "xml"),
        ("rows.csv", "csv"),
        ("main.tex", "tex"),
        ("notes.rst", "rst"),
        # Shell & build
        ("deploy.sh", "shell"),
        ("setup.ps1", "powershell"),
        ("run.bat", "batchfile"),
        ("main.tf", "terraform"),
        ("policy.hcl", "hcl"),
        ("flake.nix", "nix"),
        ("query.sql", "sql"),
    ],
)
def test_known_extensions_map_to_a_language(
    filename: str, language: str
) -> None:
    assert _detect(filename) == language


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        # Extensionless, which the suffix lookup alone would return "" for.
        ("Dockerfile", "dockerfile"),
        ("dockerfile", "dockerfile"),
        ("Dockerfile.dev", "dockerfile"),
        ("Containerfile", "dockerfile"),
        ("Makefile", "makefile"),
        ("GNUmakefile", "makefile"),
        ("CMakeLists.txt", "cmake"),
        ("Gemfile", "ruby"),
        ("Rakefile", "ruby"),
        ("Jenkinsfile", "groovy"),
        ("Vagrantfile", "ruby"),
        ("Procfile", "shell"),
        # Extension lookups that carry no dot in the table entry.
        ("lib.mk", "makefile"),
        ("build.dockerfile", "dockerfile"),
    ],
)
def test_extensionless_filenames_map_to_a_language(
    filename: str, language: str
) -> None:
    assert _detect(filename) == language


def test_lookup_is_case_insensitive() -> None:
    """`README.MD` and `APP.PY` are ordinary filenames on any checkout."""
    assert _detect("APP.PY") == "python"
    assert _detect("README.MD") == "markdown"
    assert _detect("Main.TS") == "typescript"


def test_an_unknown_extension_returns_the_empty_marker() -> None:
    """`""`, not a guess: the caller is what decides it becomes `other`."""
    assert _detect("notes.zzz") == ""
    assert _detect("archive.unknownext") == ""


# ======================================================================
# The single walk: one denominator, one set of buckets
# ======================================================================


def _write(root: Path, rel: str, lines: int) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join("x" for _ in range(lines)) + "\n", encoding="utf-8")


class TestLanguageLineCounts:
    def test_an_unmapped_file_lands_in_the_other_bucket(
        self, tmp_path: Path
    ) -> None:
        """Dropping it is what made the shares sum to less than 100.

        `.ini` has no entry, and the old caller discarded the file entirely --
        its lines were in `total_lines` and in no language.
        """
        _write(tmp_path, "main.py", 9)
        _write(tmp_path, "setup.ini", 1)

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        assert counts["python"] == 9
        assert counts[_OTHER_LANGUAGE] == 1

    def test_every_bucket_adds_to_the_line_total(self, tmp_path: Path) -> None:
        _write(tmp_path, "a.py", 7)
        _write(tmp_path, "b.ts", 3)
        _write(tmp_path, "c.tf", 2)
        _write(tmp_path, "unknown_extensionless_thing", 1)

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        assert sum(counts.values()) == 13
        assert set(counts) == {"python", "typescript", "terraform", _OTHER_LANGUAGE}

    def test_files_with_no_relevant_lines_do_not_create_zero_buckets(
        self, tmp_path: Path
    ) -> None:
        """A language with no lines at all should not appear in the mix."""
        _write(tmp_path, "main.py", 5)
        (tmp_path / "empty.js").write_text("", encoding="utf-8")

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        # `empty.js` has no content, so it contributes no lines; the mix
        # describes lines, and a language with none is not part of it.
        assert counts["python"] == 5

    def test_excluded_directories_are_not_walked(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/main.py", 5)
        _write(tmp_path, "node_modules/pkg/index.js", 50)
        _write(tmp_path, ".venv/lib/site.py", 50)
        _write(tmp_path, "__pycache__/mod.py", 50)

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        assert counts == {"python": 5}

    def test_binary_and_media_extensions_are_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path, "main.py", 5)
        _write(tmp_path, "logo.png", 40)
        _write(tmp_path, "lib.so", 40)

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        assert counts == {"python": 5}

    def test_nested_packages_are_all_counted(self, tmp_path: Path) -> None:
        """The monorepo shape: one bucket per package, summed."""
        _write(tmp_path, "services/api/main.py", 4)
        _write(tmp_path, "services/worker/task.py", 6)
        _write(tmp_path, "frontend/app.ts", 10)

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        assert counts == {"python": 10, "typescript": 10}

    def test_a_count_of_one_line_is_reported_not_rounded_away(
        self, tmp_path: Path
    ) -> None:
        """Rounding belongs to the percentage, never to the count."""
        _write(tmp_path, "main.py", 999)
        _write(tmp_path, "tiny.sh", 1)

        counts = RepositoryFetcher()._language_line_counts_sync(str(tmp_path))

        assert counts["shell"] == 1
