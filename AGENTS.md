# AGENTS.md — collaboration rules for this repo

## Project identity

- **Repo**: `r3zound/openwrt-v50-builder`
- **Purpose**: build custom OpenWrt 25.12.5 firmware for ZTE MU3351/V50 via template injection on a remote Ubuntu build server.
- **Target device**: ZTE MU3351 / V50 (ARMv8, Android-VM via crosvm).

## Directory layout (enforced)

```
.
├── README.md           # root only
├── AGENTS.md           # root only — this file
├── LICENSE             # root only
├── docs/               # long-form skill documents (Chinese OK)
├── tools/              # reusable scripts (sanitized, env-var driven)
├── archive/            # one-time scripts, organized by date+topic
│   └── <YYYY-MM-DD>-<topic>/
└── credentials/        # LOCAL ONLY, git-ignored, private credentials & original files
```

## Hard rules

1. **Never commit credentials.** SSH IPs, usernames, passwords, sudo passwords, API keys, private keys go in `credentials/` (git-ignored) or env vars. Public files must use `<YOUR_*>` placeholders.
2. **Never put scripts in the root.** New work goes into `tools/` (reusable) or `archive/<date>-<topic>/` (one-time).
3. **Docs go in `docs/`.** Markdown documentation lives there; root is reserved for the four canonical files above.
4. **One question at a time** when designing new flows. Confirm before writing destructive code.
5. **List the directory before writing.** When modifying this repo, `ls` or `Get-ChildItem` first; don't overwrite a file you didn't create.

## When you add a script

Ask yourself:

- Will this script be called again by a future agent/user? → `tools/`
- Was this for one specific session? → `archive/<YYYY-MM-DD>-<topic>/`

## Commit message convention

```
<scope>: <imperative summary>

<body: why, what changed, what to verify>
```

Scope examples: `docs`, `tools`, `archive`, `skill`, `i18n`.

## Sanitization pattern

When porting from local config-driven scripts to public-friendly versions, replace the
real server IP, username, and password with `<YOUR_*>` placeholders. For example, in
Python:

| Before (private) | After (public) |
|--------|-------|
| `<your-private-server-ip>` | `<YOUR_BUILD_SERVER_IP>` |
| `USER = '<your-private-user>'` | `USER = os.environ.get('OPENWRT_BUILD_USER', '<YOUR_USER>')` |
| `PASS = '<your-private-password>'` | `PASS = os.environ.get('OPENWRT_BUILD_PASS', '<YOUR_PASSWORD>')` |
| `echo "<your-private-password>" \| sudo -S` | `echo "$SUDO_PASS" \| sudo -S` |

After sanitization, run a final grep for the actual IP / password / username strings you
intend to remove, to verify nothing leaked into committed files.