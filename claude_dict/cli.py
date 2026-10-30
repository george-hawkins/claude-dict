"""A small command-line dictionary backed by Claude."""

import os
import re
import subprocess
import sys

import anthropic

FALLBACK_MODEL = "claude-sonnet-5-5"
KEYCHAIN_SERVICE = "anthropic-api-key"

SYSTEM = (
    "You are a concise dictionary and thesaurus. Reply with the requested "
    "content only: no preamble, no commentary, no closing remarks, no markdown."
)

PROMPTS = {
    "spell": (
        "Check the spelling of: {word}\n\n"
        "Rules:\n"
        "- If it is misspelled, reply with only the single most likely correct spelling.\n"
        "- If it is already correctly spelled, reply with exactly: correct\n"
        "- If the (corrected) spelling is the standard British English spelling and "
        "the standard American English spelling differs, add a second line: "
        "British spelling; American: <american spelling>\n"
        "- Do not mention British spelling if the word is already the American spelling "
        "or if both are the same."
    ),
    "synonym": (
        "List synonyms for: {word}\n\n"
        "Reply with a single comma-separated list of at most eight of the most common synonyms, "
        "most common first. No numbering, no explanations. If the word has more than "
        "one common sense, give synonyms for the most common one unless a sense is "
        "specified below."
    ),
    "meaning": (
        "Give the meaning of: {word}\n\n"
        "Reply with one clear, concise sentence. If there is more than one common "
        "meaning, give only the most common one unless a sense is specified below."
    ),
}

# Commands that accept a trailing "(guide)" to pick one sense of the word.
GUIDES = {
    "synonym": "Only give synonyms for the sense relating to: {guide}",
    "meaning": "Only give the sense relating to: {guide}",
}

COMMANDS = tuple(PROMPTS)
QUIT = ("quit", "exit")

GUIDE_RE = re.compile(r"\(([^)]*)\)\s*$")


def resolve_command(prefix: str) -> str | None:
    """Return the unique command starting with *prefix*, or None."""
    names = COMMANDS + QUIT
    matches = [c for c in names if c.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if prefix in matches:
        return prefix
    return None


def parse(line: str) -> tuple[str, str, str | None] | None:
    """Split a line into (command, word, guide). Returns None on bad input."""
    parts = line.strip().split(None, 1)
    if not parts:
        return None
    command = resolve_command(parts[0].lower())
    if command is None:
        return None
    rest = parts[1].strip() if len(parts) > 1 else ""
    guide = None
    if command in GUIDES:
        m = GUIDE_RE.search(rest)
        if m:
            guide = m.group(1).strip() or None
            rest = rest[: m.start()].strip()
    return command, rest, guide


def build_prompt(command: str, word: str, guide: str | None) -> str:
    prompt = PROMPTS[command].format(word=word)
    if guide:
        prompt += "\n\n" + GUIDES[command].format(guide=guide)
    return prompt


def keychain_api_key() -> str | None:
    """Read the API key from the macOS login keychain, if present.

    macOS prompts to unlock the keychain and to allow access on first use.
    """
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    key = result.stdout.strip()
    return key if result.returncode == 0 and key else None


def latest_sonnet(client: anthropic.Anthropic) -> str:
    """Return the id of the most recently released Sonnet model, or the fallback."""
    try:
        sonnets = [m for m in client.models.list(limit=100) if "sonnet" in m.id]
    except anthropic.APIError:
        return FALLBACK_MODEL
    if not sonnets:
        return FALLBACK_MODEL
    # Newest first; on a tie prefer the shorter (alias) id over a dated snapshot.
    return max(sonnets, key=lambda m: (m.created_at, -len(m.id))).id


def ask(client: anthropic.Anthropic, model: str, prompt: str) -> str:
    # Dictionary lookups need no reasoning: turn thinking off and use low
    # effort for the fastest, tersest answers. Thinking tokens would otherwise
    # count against max_tokens and could truncate the visible answer.
    response = client.messages.create(
        model=model,
        max_tokens=1000,
        thinking={"type": "between_tools"},
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "max_tokens":
        print("warning: answer was cut off by the token limit", file=sys.stderr)
    return "".join(b.text for b in response.content if b.type == "text").strip()


def usage() -> str:
    return (
        "Commands (any unique prefix works, e.g. sp, sy, m):\n"
        "  spell <word>              most likely correct spelling\n"
        "  synonym <word> [(guide)]  list synonyms, optionally for one sense\n"
        "  meaning <word> [(guide)]  concise meaning, optionally for one sense\n"
        "  quit                      exit (or Ctrl-D)"
    )


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or keychain_api_key()
    if not api_key:
        print(
            "error: ANTHROPIC_API_KEY is not set and no keychain item "
            f"with service '{KEYCHAIN_SERVICE}' was found",
            file=sys.stderr,
        )
        return 1

    try:
        import readline  # noqa: F401  (line editing and history)
    except ImportError:
        pass

    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get("CLAUDE_DICT_MODEL") or latest_sonnet(client)
    print(f"model: {model}", file=sys.stderr)

    while True:
        try:
            line = input("> ")
        except EOFError, KeyboardInterrupt:
            print()
            return 0

        if not line.strip():
            continue

        parsed = parse(line)
        if parsed is None:
            print(usage())
            continue

        command, word, guide = parsed
        if command in QUIT:
            return 0
        if not word:
            print(f"usage: {command} <word>")
            continue

        try:
            print(ask(client, model, build_prompt(command, word, guide)))
        except anthropic.APIError as e:
            print(f"error: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
