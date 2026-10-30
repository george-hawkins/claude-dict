# claude-dict

A tiny command-line dictionary and thesaurus powered by Claude Sonnet.

Start it, then type a command followed by a word (or short phrase):

```
> sp recieve
receive
> sp colour
correct
British spelling; American: color
> sy happy
cheerful, glad, joyful, content, pleased, delighted, merry, elated
> sy humanity (qualities that make us human)
compassion, kindness, benevolence, mercy, empathy, humaneness, sympathy, tenderness
> m bank (money)
A financial institution that accepts deposits, lends money and provides other financial services.
> m kick the bucket
To die.
```

## Commands

| Command   | What it does                                                                                              |
|-----------|-----------------------------------------------------------------------------------------------------------|
| `spell`   | Gives the most likely correct spelling, or `correct` if it is already right. If the word is a British spelling with a different American spelling, it says so and gives the American form. |
| `synonym` | Lists up to eight synonyms, most common first. Takes an optional `(guide)` to pick one sense.                      |
| `meaning` | Gives a clear, concise one-sentence meaning. Takes an optional `(guide)` to pick one sense.               |
| `quit`    | Exits. `exit` or Ctrl-D also work.                                                                        |

Any unique prefix of a command works: `m` for `meaning`, `sp` for `spell`, `sy` for `synonym`.
Plain `s` is ambiguous and prints the help text.

Multiple words after the command are treated as a single phrase, so `m kick the bucket` looks up the idiom.

For `meaning` and `synonym`, you can narrow the sense with a guide in parentheses at the end of the line,
for example `m bank (river)`, `m lead (metal)` or `sy humanity (qualities that make us human)`.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and an Anthropic API key. The project targets Python 3.14; `uv` downloads it automatically if it is not already installed.

```
export ANTHROPIC_API_KEY=sk-ant-...
uv run claude-dict
```

`uv run` creates the virtual environment and installs the dependencies the first time.

Alternatively, put the key in a `.env` file (ignored by git) and run `uv run --env-file .env claude-dict`.

### macOS keychain

If `ANTHROPIC_API_KEY` is not set, the app reads the key from the macOS login keychain,
looking for an item with service name `anthropic-api-key`. Add it with:

```
security add-generic-password -s anthropic-api-key -a "$USER" -l "Anthropic API key" -w
```

The `-w` with no value prompts for the key, so it never lands in your shell history.
On first run macOS asks whether `security` may read the item; choose "Always Allow".

This is the login keychain, not the Passwords app. Passwords is the front end to iCloud
Keychain, which only Apple's AutoFill and entitled apps can read. The login keychain is
the store that command-line tools such as Git, the AWS CLI and `security` use, and it is
the right home for machine secrets like API keys.

Other useful commands:

```
security find-generic-password -s anthropic-api-key -w   # print the key
security delete-generic-password -s anthropic-api-key    # remove it
```

## Model

On startup the app queries the Anthropic Models API and uses the most recently released
Sonnet model it finds, printing `model: <id>` to stderr. If the query fails it falls back
to `claude-sonnet-5-5`. Set `CLAUDE_DICT_MODEL` to pin a model instead.

## Configuration

| Variable            | Purpose                                             | Default             |
|---------------------|-----------------------------------------------------|---------------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required).                  |                     |
| `CLAUDE_DICT_MODEL` | Pin a specific model instead of auto-detecting.     | newest Sonnet       |

## Layout

```
claude_dict/cli.py   the whole app: command parsing, prompts, REPL loop
claude_dict/__init__.py  marks the package (required by the uv build backend)
pyproject.toml       project metadata and the `claude-dict` script entry point
```
