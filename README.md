# Key Manager

Desktop app for managing **SSH** (`~/.ssh/config`) and **AWS CLI** (`~/.aws/config`, `~/.aws/credentials`) profiles. Runs in the system tray with quick connect actions.

## Features

- Edit SSH hosts, keys, ProxyJump, and open terminals per host
- Generate SSH keys, copy to `authorized_keys`, rotate keys
- Edit AWS config and credentials profiles
- System tray menu with per-host **Connect** / **Open terminal**

## Requirements

- Python 3.11+
- Windows: [OpenSSH Client](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) (for terminal and key tools)
- Optional: [Windows Terminal](https://aka.ms/terminal) for `wt` integration

## Run from source

```powershell
pip install -r requirements.txt
python main.py
```

Disable system tray (window close quits the app):

```powershell
python main.py --no-tray
```

CLI helpers:

```powershell
python apply_ssh_key.py -k ~/.ssh/id_ed25519 -u ubuntu -H my-server
python swap_ssh_key.py -H my-server -u ubuntu -o ~/.ssh/id_old -n ~/.ssh/id_new
```

## Releases

Tagged releases are built on GitHub Actions (Windows x64):

| Tag        | Produces |
|------------|----------|
| `v1.2.3`   | `KeyManager-1.2.3.exe` (portable) |
|            | `KeyManager-1.2.3-setup.exe` (installer) |

The version is embedded in the app title, Windows file properties, executable name, and installer.

### Create a release

```bash
git tag v0.1.0
git push origin v0.1.0
```

The [Release workflow](.github/workflows/release.yml) runs on tag push.

### Local build (Windows)

```powershell
pip install -r requirements.txt -r requirements-build.txt
python scripts/set_version.py 0.1.0
$env:APP_VERSION = "0.1.0"
pyinstaller packaging/KeyManager.spec --noconfirm --clean
# Optional installer (requires Inno Setup):
iscc installer\KeyManager.iss /DAppVersion=0.1.0 /DSourceDir=..\dist
```

Output: `dist/KeyManager-0.1.0.exe`

## Project layout

```
Key-Manager/
  main.py                 # GUI entry point
  ssh_config_gui/         # Application package
  scripts/set_version.py  # Version stamping for builds
  packaging/KeyManager.spec
  installer/KeyManager.iss
  .github/workflows/release.yml
```

## License

MIT (add your license file if needed)
