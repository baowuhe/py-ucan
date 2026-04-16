# py-ucan

A wrapper for yt-dlp to get video titles and download videos.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- [deno](https://deno.land/)

## Installation

```shell
pip install py-ucan
```

Or run directly:

```shell
uvx py-ucan --help
```

## Configuration

Create config file at `~/.local/share/py-ucan/config.toml`:

```toml
[global]
# Proxy pool (supports http/https/socks5, multiple proxies supported)
# This is shared across all platforms and can be overridden per-platform
proxy_pool = [
    "socks5://192.168.2.61:6665",
    "http://127.0.0.1:8080",
]

[youtube]
# Cookie file path (required for login verification)
# Supports separate cookie files for mobile and PC
# Uses mobile cookie when URL domain is m.youtube.com, otherwise uses PC cookie
cookies_pc = "/path/to/cookies.txt"
cookies_mobile = "/path/to/cookies_mobile.txt"

# Remote template path
remote_template = "ejs:github"

# Download temp directory
temp_path = "/tmp/youtube/"

# Download save directory
home_path = "/path/to/videos/"

# Video format (default)
format = "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv+ba/b"

# Max retries (0 means no retry)
max_retries = 3

# Retry delay (seconds)
retry_delay = 6
```

### Configuration Precedence

- `proxy_pool`: If set in `[youtube]`, uses that; otherwise falls back to `[global]`
- Other settings: `[youtube]` overrides `[global]` for platform-specific configurations

## Usage

### Show Configuration

```shell
py-ucan show config
```

### Get Video Info

```shell
py-ucan info youtube <VIDEO_URL>
```

### Download Video

```shell
py-ucan down youtube <VIDEO_URL>
```

### Download with Custom Name

```shell
py-ucan down youtube <VIDEO_URL> <NAME>
```

## Options

- `--verbose`: Print debug info

## Commands

- `show config`: Print current config file content
- `info youtube`: Get title and upload date of a YouTube video
- `down youtube`: Download a video from YouTube
