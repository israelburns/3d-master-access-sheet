#!/usr/bin/env python3
"""
3D Master Access Sheet - Build Script
Parses MASTER_ACCESS_SHEET.txt into structured JSON for the VR world.
Categorizes sections into wings (Walmart-style departments).

Usage: python build.py
Output: data/sections.json
"""

import json
import re
import os
import html
import textwrap

# Patterns that look like secrets/tokens/keys/passwords
SECRET_PATTERNS = [
    r'(?:sk-|xai-|r8_|hf_|ghp_|gho_|glpat-|AKIA)[A-Za-z0-9_\-]{10,}',  # API keys
    r'(?:password|passwd|pwd|token|secret|key|api.?key)\s*[:=]\s*\S+',  # key=value secrets
    r'(?:Bearer|Basic)\s+[A-Za-z0-9+/=_\-]{20,}',  # Auth headers
    r'\b[A-Za-z0-9+/]{40,}\b',  # Long base64-like tokens
]

def redact_secrets(text):
    """Replace anything that looks like a secret/token/key with [REDACTED]."""
    result = text
    for pattern in SECRET_PATTERNS:
        result = re.sub(pattern, '[REDACTED]', result, flags=re.IGNORECASE)
    return result

MASTER_SHEET = os.path.expanduser(r"~\Money_Codes\master-access\MASTER_ACCESS_SHEET.txt")
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "sections.json")

# Wing definitions - organize sections by category
# Each wing is a corridor in the 3D world
WINGS = {
    "COMMAND CENTER": {
        "id": "command",
        "color": "#ff4444",
        "description": "Laws, directives, protocols",
        "sections": []  # filled by categorizer
    },
    "OPERATIONS": {
        "id": "ops",
        "color": "#44aaff",
        "description": "Session status, active issues, capabilities",
        "sections": []
    },
    "CREDENTIALS VAULT": {
        "id": "vault",
        "color": "#d4a853",
        "description": "Access keys, servers, accounts",
        "sections": []
    },
    "PROJECTS & TOOLS": {
        "id": "projects",
        "color": "#3fb950",
        "description": "Project links, deploy tools, automations",
        "sections": []
    },
    "COMMS & LOGS": {
        "id": "comms",
        "color": "#bc8cff",
        "description": "Communications, session logs, preferences",
        "sections": []
    },
}

# Map section indices (0-based) to wings
SECTION_WING_MAP = {
    # COMMAND CENTER - Laws and directives
    2: "COMMAND CENTER",   # Cartesian Prime Directive
    3: "COMMAND CENTER",   # Save Money Philosophy
    4: "COMMAND CENTER",   # Task Masters Dedup
    5: "COMMAND CENTER",   # No Relays Rule
    6: "COMMAND CENTER",   # No Impersonation
    7: "COMMAND CENTER",   # Continuity System

    # OPERATIONS - Active work and capabilities
    8: "OPERATIONS",       # Current Session Status
    9: "OPERATIONS",       # LLM Browser Automation
    10: "OPERATIONS",      # Claude Multi-Agent
    11: "OPERATIONS",      # LLM Start Here
    12: "OPERATIONS",      # Security Notice

    # CREDENTIALS VAULT - Access and accounts
    13: "CREDENTIALS VAULT",  # Local Machine
    14: "CREDENTIALS VAULT",  # GitHub
    15: "CREDENTIALS VAULT",  # Personal Server FTP
    16: "CREDENTIALS VAULT",  # Email Accounts
    17: "CREDENTIALS VAULT",  # Phone
    18: "CREDENTIALS VAULT",  # Cloud Services
    19: "CREDENTIALS VAULT",  # Crypto / Web3

    # PROJECTS & TOOLS - Links, deploy, automation
    20: "PROJECTS & TOOLS",   # Project Links
    21: "PROJECTS & TOOLS",   # Web Analytics
    22: "PROJECTS & TOOLS",   # Sync & Deploy Tools
    23: "PROJECTS & TOOLS",   # Google Contacts
    24: "PROJECTS & TOOLS",   # Google Docs Upload
    25: "PROJECTS & TOOLS",   # Quick Commands

    # COMMS & LOGS - Communications and session data
    0: "COMMS & LOGS",        # Jeremy Comms Roadmap
    1: "COMMS & LOGS",        # Jeremy Quick Reference
    26: "COMMS & LOGS",       # Session Log
    27: "COMMS & LOGS",       # Interaction Preferences
    28: "COMMS & LOGS",       # Notes
    29: "COMMS & LOGS",       # Kimi API Access
}


def parse_master_sheet(filepath):
    """Parse the master access sheet into sections."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    pattern = r"={50,}\n\s*(.+?)\n={50,}"
    matches = list(re.finditer(pattern, raw))
    sections = []

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        title_clean = re.sub(r"[^\x20-\x7E]", "", title).strip()
        if not title_clean:
            title_clean = f"Section {i + 1}"

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()

        # Clean body
        body = re.sub(r"[┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬]", "", body)
        body = re.sub(r"[^\x0a\x0d\x20-\x7E]", "", body)

        # Extract subsections (lines starting with --- headers)
        subsections = []
        for sm in re.finditer(r"-{30,}\n\s*(.+?)\n-{30,}", body):
            subsections.append(sm.group(1).strip())

        # Count status markers
        active_count = len(re.findall(r"Status:\s*(ACTIVE|CONNECTED|LIVE|COMPLETE|WORKING|DEPLOYED|OPERATIONAL)", body))
        blocked_count = len(re.findall(r"Status:\s*(BLOCKED|DOWN|FAILED|DEAD)", body))
        todo_count = body.count("[ ]")
        done_count = body.count("[x]") + body.count("[X]")

        # Redact secrets from body for safe storage/push
        redacted_body = redact_secrets(body)

        sections.append({
            "index": i,
            "title": title_clean,
            "body": redacted_body,
            "line_count": body.count("\n") + 1,
            "char_count": len(body),
            "subsections": subsections,
            "stats": {
                "active": active_count,
                "blocked": blocked_count,
                "todo": todo_count,
                "done": done_count,
            },
        })

    return sections


def categorize_into_wings(sections):
    """Assign sections to wings based on SECTION_WING_MAP."""
    wings = {}
    for name, wing in WINGS.items():
        wings[name] = {**wing, "sections": []}

    for section in sections:
        wing_name = SECTION_WING_MAP.get(section["index"], "COMMS & LOGS")
        # Create aisle reference
        wing = wings[wing_name]
        aisle_num = len(wing["sections"]) + 1
        section["aisle"] = f"{wing['id'][0].upper()}{aisle_num}"
        section["wing"] = wing_name
        wing["sections"].append(section)

    return wings


def main():
    print("Parsing Master Access Sheet...")
    sections = parse_master_sheet(MASTER_SHEET)
    print(f"  Found {len(sections)} sections")

    print("Categorizing into wings...")
    wings = categorize_into_wings(sections)

    for name, wing in wings.items():
        count = len(wing["sections"])
        print(f"  {name}: {count} sections ({wing['description']})")

    # Build output
    output = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "total_sections": len(sections),
        "wings": {},
        "github_raw_url": "https://raw.githubusercontent.com/israelburns/master-access/main/MASTER_ACCESS_SHEET.txt",
    }

    for name, wing in wings.items():
        output["wings"][name] = {
            "id": wing["id"],
            "color": wing["color"],
            "description": wing["description"],
            "section_count": len(wing["sections"]),
            "sections": [
                {
                    "index": s["index"],
                    "title": s["title"],
                    "aisle": s["aisle"],
                    "line_count": s["line_count"],
                    "char_count": s["char_count"],
                    "subsections": s["subsections"],
                    "stats": s["stats"],
                    "body": s["body"],
                }
                for s in wing["sections"]
            ],
        }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    size = os.path.getsize(OUTPUT)
    print(f"\nOutput: {OUTPUT}")
    print(f"Size: {size:,} bytes")
    print("Done!")


if __name__ == "__main__":
    main()
