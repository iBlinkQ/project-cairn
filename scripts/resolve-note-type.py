#!/usr/bin/env python3
"""Read-only note identity resolution for init, maintenance and graduation.

Requires Python 3 + PyYAML. Prints JSON; never writes configuration or notes.
Project: --project-config .cairn/config.yaml
New init: --init [--user-config FILE] (--selection TYPE | --skip | --reuse)
"""
import argparse
import json
from pathlib import Path

import yaml


def valid_type(value):
    if not isinstance(value, str) or any(c in value for c in "\r\n\u2028\u2029"):
        raise ValueError("note_type must be a non-empty, single-line string")
    value = value.strip()
    if not value:
        raise ValueError("note_type must be a non-empty, single-line string")
    return value


def read_config(path, optional=False):
    path = Path(path)
    if optional and not path.exists():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: configuration must be a mapping")
    return value


def result(topic_type, knowledge_type, source, legacy=False):
    return {
        "topic_type": topic_type,
        "knowledge_type": knowledge_type,
        "topic_type_yaml": json.dumps(topic_type, ensure_ascii=False),
        "knowledge_type_yaml": json.dumps(knowledge_type, ensure_ascii=False),
        "source": source,
        "legacy": legacy,
    }


def project_types(path):
    config = read_config(path)
    cairn = config.get("cairn", {})
    if not isinstance(cairn, dict):
        raise ValueError("cairn must be a mapping")
    if "note_type" not in cairn:
        # Deliberately never consult personal defaults for an existing project.
        return result("project_topic", "knowledge_note", "legacy_project", True)
    note_type = valid_type(cairn["note_type"])
    return result(note_type, note_type, "project_config")


def init_types(user_config=None, selection=None, skip=False, reuse=False):
    if selection is not None:
        note_type = valid_type(selection)
        return result(note_type, note_type, "selection")
    if not (skip or reuse):
        raise ValueError("no answer: provide --selection, explicit --skip, or --reuse")
    config = read_config(user_config, optional=True) if user_config else {}
    defaults = config.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be a mapping")
    if "note_type" in defaults:
        note_type = valid_type(defaults["note_type"])
        return result(note_type, note_type, "saved_default")
    if reuse:
        raise ValueError("no saved defaults.note_type: ask for a selection or explicit skip")
    return result("project_insight", "project_insight", "explicit_skip_fallback")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--project-config")
    mode.add_argument("--init", action="store_true")
    parser.add_argument("--user-config")
    answer = parser.add_mutually_exclusive_group()
    answer.add_argument("--selection")
    answer.add_argument("--skip", action="store_true")
    answer.add_argument("--reuse", action="store_true")
    args = parser.parse_args()
    if args.project_config and (args.user_config or args.selection is not None or args.skip or args.reuse):
        parser.error("project resolution accepts only --project-config; it never inherits user defaults")
    try:
        resolved = project_types(args.project_config) if args.project_config else init_types(
            args.user_config, args.selection, args.skip, args.reuse
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(json.dumps(resolved, ensure_ascii=False))


if __name__ == "__main__":
    main()
