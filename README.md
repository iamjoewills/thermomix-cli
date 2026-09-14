# Thermomix CLI

Manage your Cookidoo account from the Terminal on a Mac: look up recipes, copy
them into your own Created Recipes, organise collections, plan your week and
build the shopping list.

It is one command, `thermomix-cli`, with a short first-run wizard. You do not
need to know Python, and nothing else needs installing first.

---

## ⚠️ Read this before you install

**Cookidoo has no official public API.** This tool works by making the same web
requests the Cookidoo website makes, using your own Cookidoo login.

- It is **not** made, supported, endorsed or approved by Vorwerk or Cookidoo.
- It can **stop working at any time**, without warning, if Cookidoo changes how
  its site works. There is no guarantee it will keep working, and no promise of
  updates or support.
- It talks to the **Cookidoo website only**. It does not connect to, control or
  operate a Thermomix appliance. Recipes you put on your Cookidoo account show
  up on the machine the same way they would if you had added them on the
  website – you still cook them yourself, on the device.
- It uses your Cookidoo credentials. Check whether that is something you are
  comfortable with, and whether it fits Cookidoo's own terms, before you start.
- Some commands change your account: importing a recipe, planning a day,
  editing collections, adding to your shopping list. Deleting is always
  confirmed first.

Thermomix® and Cookidoo® are trademarks of Vorwerk. This project is not
affiliated with them.

---

## Getting started

**[SETUP.md](SETUP.md) is the step-by-step guide** – how to open Terminal, what
to paste in, how to enter your Cookidoo details safely, how to check it worked,
and how to update or remove it later. Start there if you are not used to the
Terminal.

The short version, for people who already are:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/iamjoewills/thermomix-cli/main/install.sh)"
```

Then, in a new Terminal window:

```bash
thermomix-cli setup        # asks for your Cookidoo email and password
thermomix-cli auth whoami  # proves it worked, changes nothing
```

The installer puts everything in two folders it owns
(`~/.local/share/thermomix-cli` and `~/.local/bin/thermomix-cli`), adds one
marked line to `~/.zshrc`, and never uses `sudo`. Run it again to update.
[`uninstall.sh`](uninstall.sh) removes all of it.

Requirements: a Mac, an internet connection, and a Cookidoo account. The
installer downloads its own private copy of Python, so nothing already on your
Mac is changed. Tested on macOS 26.6.2, Apple Silicon – see
[Platforms](#platforms) for what that does and does not cover.

---

## Where your password is kept

`thermomix-cli setup` saves your details in one file:

```
~/.config/thermomix-cli/config.json
```

It is created so that only your own user account can read it (mode `600`, in a
`700` folder). Nothing is sent anywhere except to Cookidoo when you run a
command, and the password is never printed, never logged and never written to
this repository.

- `thermomix-cli setup --show` – what is saved, with the password shown only as
  "saved"
- `thermomix-cli setup --forget` – delete the saved details from this Mac

If you would rather not save anything, set `COOKIDOO_EMAIL` and
`COOKIDOO_PASSWORD` in the environment instead; they take precedence.

---

## What it can do

```
thermomix-cli setup                    save or review your Cookidoo details
thermomix-cli version                  which version is installed

thermomix-cli auth login               check your details work
thermomix-cli auth whoami              which account you are signed in as
thermomix-cli auth subscription        the subscription on the account

thermomix-cli locale countries         country codes Cookidoo serves
thermomix-cli locale languages         languages Cookidoo serves
thermomix-cli locale list --country gb --language en-GB

thermomix-cli recipe get r59322        read an official recipe
thermomix-cli recipe get r59322 --raw  the same, as JSON

thermomix-cli custom-recipe import r59322              copy it into your own
thermomix-cli custom-recipe import r59322 --servings 4
thermomix-cli custom-recipe list                       your created recipes
thermomix-cli custom-recipe get <id> [--annotations]
thermomix-cli custom-recipe remove <id>                asks first

thermomix-cli collection managed list                  Cookidoo's collections
thermomix-cli collection managed add col500401
thermomix-cli collection managed remove col500401
thermomix-cli collection custom list                   your own collections
thermomix-cli collection custom create "Sourdough"
thermomix-cli collection custom add-recipe <collection_id> <recipe_id>
thermomix-cli collection custom remove-recipe <collection_id> <recipe_id>
thermomix-cli collection custom remove <collection_id>

thermomix-cli calendar week                            My Week, as a table
thermomix-cli calendar week --on 2026-05-12
thermomix-cli calendar add r59322 --on 2026-05-12
thermomix-cli calendar add-custom <id> --on 2026-05-12
thermomix-cli calendar remove r59322 --on 2026-05-12
thermomix-cli calendar remove-custom <id> --on 2026-05-12

thermomix-cli shopping recipes                         what is on the list
thermomix-cli shopping ingredients
thermomix-cli shopping additional
thermomix-cli shopping add-recipe r59322 [--custom]
thermomix-cli shopping remove-recipe r59322 [--custom]
thermomix-cli shopping add-item Salt Butter "Strong flour"
thermomix-cli shopping check <item_id> [--additional]
thermomix-cli shopping remove-item <item_id>
thermomix-cli shopping clear                           asks first
```

Created Recipes are a Cookidoo premium feature. `thermomix-cli auth
subscription` tells you whether the account has one.

Every command takes `--help`.

## What it does not do

- It does not write recipes from scratch, and it does not author guided-cooking
  step annotations. Those live in a separate private build and are not part of
  this public tool.
- It does not connect to a Thermomix directly, over the network or otherwise.
- It does not sync with any note-taking app, workspace or plugin. The tool is
  self-contained: a Cookidoo account is the only thing it needs.

## Platforms

| Platform | Status |
|---|---|
| macOS 26.6.2, Apple Silicon | **Tested.** Install, update, failed-update rollback and uninstall all run end to end, into a clean home folder with only the system directories on the path. That is a fresh environment on a working Mac, not a freshly-installed operating system. |
| macOS on Intel | **Implemented, not proven.** The installer picks the `x86_64` download and checks its own published checksum, but no Intel Mac was available, so that path has never actually been run. Expect it to work; do not take this as evidence that it does. |
| Windows | **Unsupported.** `install.sh`, the command shim and the PATH step are shell scripts that do not run on Windows. No Windows machine was available. The macOS testing above says nothing about Windows. |
| Linux | Not attempted. |

## Credits

Built on [`cookidoo-api`](https://github.com/miaucl/cookidoo-api) by miaucl, and
on Typer, Rich, aiohttp and uv. See [NOTICE.md](NOTICE.md).

## Licence

**You may install and run this tool for personal use.** All other rights are
reserved. Third-party dependencies retain their own licences.
