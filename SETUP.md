# Setting up Thermomix CLI on a Mac

A step-by-step guide. It assumes you have never used the Terminal before. Read
the warning first – it matters more than the instructions.

---

## Before you start: what this is

Cookidoo has **no official public API**. This tool signs in to Cookidoo as you,
using the same web requests the Cookidoo website uses.

- It is not made, supported, endorsed or approved by Vorwerk or Cookidoo.
- Cookidoo can change its website at any time and this tool will simply stop
  working. Nobody is promising it will keep working, or that it will be fixed.
- It does **not** connect to your Thermomix. It only changes what is on your
  Cookidoo account – the same things you could change on the website yourself.
- It needs your Cookidoo email and password. Decide whether you are happy with
  that, and whether it sits right with Cookidoo's own terms, before going on.

If any of that is not acceptable to you, stop here. Nothing has been installed.

---

## What you need

- **A Mac.** This guide was written and tested on macOS 26.6.2 with Apple
  Silicon. The installer also handles Intel Macs, but no Intel Mac was
  available to try it on.
- **An internet connection.**
- **A Cookidoo account** – the email address and password you use at
  [cookidoo.co.uk](https://cookidoo.co.uk). If you want to use Created Recipes,
  that account also needs an active Cookidoo subscription.
- **About five minutes.** Most of it is waiting for a download.

You do **not** need Python, Homebrew, Xcode, an Apple developer account, or an
administrator password. The installer brings its own private copy of Python and
puts everything in your own home folder.

---

## Step 1 – Open Terminal

Terminal is an app that comes with every Mac.

1. Press **⌘ Space** (Command and the space bar together). A search box appears
   in the middle of the screen.
2. Type **terminal**.
3. Press **Return**.

A window opens with some small text and a blinking cursor. That is Terminal.
Anything below that looks like `this` gets typed – or better, pasted – into that
window, then you press **Return**.

Nothing happens until you press Return. If you paste the wrong thing, press
**Control-C** to cancel and start again.

---

## Step 2 – Install it

Copy this whole line. It is one line, even if it wraps on screen.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/iamjoewills/thermomix-cli/main/install.sh)"
```

Paste it into Terminal (**⌘ V**) and press **Return**.

You will see it work through four steps. The Python download is the slow one –
give it up to a couple of minutes on a slow connection.

**What success looks like.** The last thing it prints is:

```
==> Checking it works
    thermomix-cli 0.3.0

Done.

Open a NEW Terminal window, then run:

    thermomix-cli setup
```

If instead you see a line starting `Something stopped the install:`, read what
it says – it is written to tell you what to do. Nothing has been half-installed;
the script stops rather than leaving a mess.

### Step 3 – Open a new Terminal window

Press **⌘ N**. This matters: the new `thermomix-cli` command only exists in
windows opened after the install.

---

## Step 4 – Give it your Cookidoo details

In the new window, type:

```bash
thermomix-cli setup
```

It asks you three things:

1. **Your Cookidoo email address.** Type it and press Return.
2. **Your Cookidoo password.** *Nothing appears as you type – no dots, no
   stars, nothing.* That is deliberate: the password is never shown on screen.
   Type it and press Return, then type it a second time to check for typos.
   If the two do not match it says so and asks again.
3. **Your country and language.** Press Return twice to accept `gb` and `en-GB`.
   Elsewhere? Run `thermomix-cli locale list` afterwards to find your codes,
   then run `thermomix-cli setup` again.

It finishes by telling you where it saved things:

```
Saved to /Users/<your-name>/.config/thermomix-cli/config.json
Only your user account can read that file. The password is not shown again.
```

**Where your password lives.** In that one file, on this Mac, readable only by
your own user account. It is not sent anywhere except to Cookidoo when you run a
command, it is never printed, and it is never put into the project's code.

---

## Step 5 – Check it worked

Two harmless commands. Neither changes anything on your account.

```bash
thermomix-cli auth login
```

Success looks like:

```
Signed in. Your details work.
Next, try: thermomix-cli auth whoami
```

Then:

```bash
thermomix-cli auth whoami
```

Success looks like your Cookidoo profile name in a small table:

```
username   YourCookidooName

That is your Cookidoo profile name. Run `thermomix-cli setup --show` for the
email this Mac uses.
```

Cookidoo sends back the profile name you chose on their site, not the email
address you signed in with – so seeing a name rather than your email is the
expected result, and it confirms the sign-in worked. If you have never set a
profile name it may be short or unfamiliar; that is still a success. To check
which email address this Mac is configured with, run `thermomix-cli setup --show`.

That is it. You are set up.

Optionally, check whether the account can use Created Recipes:

```bash
thermomix-cli auth subscription
```

---

## Step 6 – Try something

```bash
thermomix-cli calendar week
```

shows what is planned in Cookidoo's My Week – the list your Thermomix shows
under Today.

```bash
thermomix-cli shopping ingredients
```

shows what is on your Cookidoo shopping list.

```bash
thermomix-cli --help
```

lists everything, and every command takes `--help` of its own, for example
`thermomix-cli calendar --help`.

---

## When something goes wrong

**`command not found: thermomix-cli`**
The window was open before you installed. Open a new one with **⌘ N**. Still
not found? Run this to check the command is there:
`ls ~/.local/bin/thermomix-cli`. If it is, run `source ~/.zshrc` and try again.

**`No Cookidoo details saved yet.`**
Setup has not been run, or it was cancelled. Run `thermomix-cli setup`.

**`Cookidoo would not accept those details.`**
The email or password is wrong. Check by signing in at
[cookidoo.co.uk](https://cookidoo.co.uk) in a browser, then run
`thermomix-cli setup` again. If you have just changed your Cookidoo password,
this is what you would expect to see.

**`Could not reach Cookidoo.`**
No internet, or Cookidoo is down. Try again in a few minutes.

**`Cookidoo has no site for country '…'`**
The country or language code is wrong. Run `thermomix-cli locale list` to see
the valid ones, then `thermomix-cli setup` to correct it.

**`No active subscription.`**
Reading recipes still works. Created Recipes need an active Cookidoo
subscription on the account.

**Something else, or a message you cannot make sense of.**
Run the same command again with more detail turned on:

```bash
THERMOMIX_CLI_DEBUG=1 thermomix-cli auth whoami
```

That prints the technical error. Your password is removed from anything it
prints, so the output is safe to paste into a bug report – but read it before
you send it anywhere.

**It worked yesterday and today everything fails.**
This is the expected end of an unofficial tool: Cookidoo may have changed its
website. There is no fix you can apply from your side.

---

## Updating

Run exactly the same command as the install:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/iamjoewills/thermomix-cli/main/install.sh)"
```

It replaces the app with the current version and leaves your saved Cookidoo
details alone. Running it when you are already up to date is harmless – it just
does the same work again. Check the result with:

```bash
thermomix-cli version
```

---

## Removing it

If you still have the downloaded project folder, run `bash uninstall.sh` from
inside it. Otherwise, one line does the same thing:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/iamjoewills/thermomix-cli/main/uninstall.sh)"
```

It removes the app folder, the command, and the line it added to `~/.zshrc`. It
only removes things it put there; anything else with the same name is left
alone, and it says so.

**Your saved Cookidoo email and password are a separate question.** The
uninstaller asks whether to delete them, and keeps them if you do not answer.
To decide up front:

```bash
bash uninstall.sh --remove-credentials   # delete them too
bash uninstall.sh --keep-credentials     # leave them, do not ask
```

You can also delete them at any time without uninstalling:

```bash
thermomix-cli setup --forget
```

Your Cookidoo account, your recipes and your Thermomix are never touched by any
of this.

---

## Using it

You may install and run this tool for personal use. All other rights are
reserved. The libraries it is built on keep their own licences.

---

## Not on a Mac?

**Windows is unsupported.** The installer, the command shim and the PATH step
are shell scripts that do not run on Windows. No Windows machine was available
to test on, so this guide makes no claim that it works there. Do not treat the
macOS testing above as evidence about Windows.

**Intel Macs** use the same installer, which picks the Intel download and
verifies its published checksum. That path has not been run on an actual Intel
Mac, so it is implemented rather than proven.

Linux has not been attempted.
