import json
import os
import socket
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse

import click
import shutil


def check_required_commands() -> None:
    """Check if required commands are installed."""
    required = ["uv", "uvx", "deno"]
    missing = []
    for cmd in required:
        if shutil.which(cmd) is None:
            missing.append(cmd)
    if missing:
        click.echo(f"Error: Missing required commands: {', '.join(missing)}", err=True)
        raise SystemExit(1)


def check_proxy(proxy: str, timeout: float = 2.0) -> bool:
    """Check if a proxy is reachable."""
    try:
        parsed = urlparse(proxy)
        host = parsed.hostname
        port = parsed.port or (1080 if parsed.scheme == "socks5" else 8080)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.error, OSError):
        return False


def get_first_available_proxy(proxies: list[str]) -> str | None:
    """Return the first proxy that is reachable."""
    for proxy in proxies:
        if check_proxy(proxy):
            return proxy
    return None


def is_mobile_url(video_url: str) -> bool:
    """Check if the video URL is for mobile (m.youtube.com)."""
    parsed = urlparse(video_url)
    return parsed.netloc == "m.youtube.com"


def validate_url(url: str) -> bool:
    """Validate that the URL has a valid scheme and netloc."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except (ValueError, AttributeError):
        return False


def validate_cookie_file(path: str) -> bool:
    """Validate that the cookie file exists and is readable."""
    p = Path(path)
    return p.exists() and p.is_file()


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_config() -> dict:
    """Load configuration from config.toml files."""
    config = {}

    # Search paths: only ~/.local/share/py-ucan/config.toml now
    config_path = Path.home() / ".local" / "share" / "py-ucan" / "config.toml"

    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

    # Merge global and youtube sections
    merged = {}

    # Start with global section (proxy_pool lives here)
    if "global" in config:
        merged.update(config["global"])

    # Youtube section overrides global for platform-specific settings
    if "youtube" in config:
        merged.update(config["youtube"])

    # Resolve proxy_pool: prioritize youtube section, fallback to global
    proxy_pool = config.get("youtube", {}).get("proxy_pool") or config.get("global", {}).get("proxy_pool")
    if proxy_pool:
        merged["proxy"] = get_first_available_proxy(proxy_pool)

    return merged


def build_base_cmd(config: dict, video_url: str = "") -> list[str]:
    """Build base yt-dlp command arguments from config."""
    cmd = ["uvx", "yt-dlp"]

    # Select cookie file based on URL type
    if video_url and is_mobile_url(video_url):
        cookies = config.get("cookies_mobile")
    else:
        cookies = config.get("cookies_pc")

    if not cookies:
        click.echo("Error: Cookie file path is empty. Please set cookies_pc or cookies_mobile in config.", err=True)
        raise SystemExit(1)
    if not validate_cookie_file(cookies):
        click.echo(f"Error: Cookie file not found or not readable: {cookies}", err=True)
        raise SystemExit(1)
    cmd.extend(["--cookies", cookies])

    if proxy := config.get("proxy"):
        cmd.extend(["--proxy", proxy])

    if remote_template := config.get("remote_template"):
        cmd.extend(["--remote-components", remote_template])

    if max_retries := config.get("max_retries", 0):
        cmd.extend(["--retries", str(max_retries)])

    if retry_delay := config.get("retry_delay"):
        cmd.extend(["--retry-sleep", f"linear={retry_delay}"])

    return cmd


def sanitize_filename(title: str, max_len: int = 60) -> str:
    """Sanitize filename: replace invalid chars with underscore, truncate to max_len."""
    import re

    # Replace invalid filesystem characters and whitespace with underscore
    # Invalid chars: / \ : * ? " < > |
    filename = re.sub(r'[/\\:*?"<>|\s]+', '_', title)

    # Truncate to max_len, being careful not to cut multi-byte characters
    if len(filename) > max_len:
        # Truncate from the end, respecting character boundaries
        truncated = filename[:max_len]
        # If we're in the middle of a multi-byte char, backtrack
        while truncated and ord(truncated[-1]) > 127 and len(truncated.encode()) > max_len:
            truncated = truncated[:-1]
        # If the last char is still potentially cut, remove it
        try:
            truncated.encode('utf-8')
            filename = truncated
        except UnicodeEncodeError:
            filename = truncated[:-1]

    return filename


@click.group()
@click.option("--verbose", is_flag=True, help="Print py-ucan debug info")
@click.pass_context
def main(ctx, verbose):
    """A wrapper for yt-dlp to get video titles and download videos."""
    check_required_commands()
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.group()
def show():
    """Show various information."""
    pass


@show.command()
def config():
    """Print the current config file content."""
    config_path = Path.home() / ".local" / "share" / "py-ucan" / "config.toml"

    if config_path.exists():
        with open(config_path) as f:
            click.echo(f"# {config_path}")
            click.echo(f.read())
    else:
        click.echo("No config file found.")


@main.group()
def info():
    """Get video information from various sources."""
    pass


@info.command()
@click.argument("video_url")
@click.pass_obj
def youtube(obj, video_url: str):
    """Get the title and upload date of a YouTube video."""
    if not validate_url(video_url):
        click.echo(f"Error: Invalid URL: {video_url}", err=True)
        raise SystemExit(1)
    verbose = obj.get("verbose", False)
    config = get_config()
    cmd = build_base_cmd(config, video_url)
    cmd.extend(["--dump-json", video_url])

    if verbose:
        click.echo(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        data = json.loads(result.stdout)
        output = {
            "title": data.get("title"),
            "description": data.get("description"),
            "upload_date": data.get("upload_date"),
        }
        click.echo(json.dumps(output, ensure_ascii=False))
    if result.stderr:
        click.echo(result.stderr, err=True)


@info.command()
@click.argument("playlist_url")
@click.pass_obj
def youtube_list(obj, playlist_url: str):
    """Get the metadata of a YouTube playlist."""
    if not validate_url(playlist_url):
        click.echo(f"Error: Invalid URL: {playlist_url}", err=True)
        raise SystemExit(1)
    verbose = obj.get("verbose", False)
    config = get_config()
    cmd = build_base_cmd(config, playlist_url)
    cmd.extend(["--dump-json", "--flat-playlist", playlist_url])

    if verbose:
        click.echo(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and result.stderr:
        click.echo(result.stderr, err=True)
        raise SystemExit(1)

    if result.stdout:
        entries = []
        playlist_title = ""
        playlist_id = ""

        for line in result.stdout.strip().split("\n"):
            if line:
                data = json.loads(line)
                if not playlist_title:
                    playlist_title = data.get("playlist_title", "")
                    playlist_id = data.get("playlist_id", "")
                entries.append({
                    "title": data.get("title", ""),
                    "upload_date": data.get("upload_date", ""),
                    "url": data.get("url", ""),
                    "playlist_index": data.get("playlist_index", 0),
                })

        output = {
            "playlist_title": playlist_title,
            "playlist_id": playlist_id,
            "playlist": entries,
        }
        click.echo(json.dumps(output, ensure_ascii=False))


@main.group()
def down():
    """Download videos from various sources."""
    pass


@down.command()
@click.argument("video_url")
@click.argument("name", required=False, default=None)
@click.pass_obj
def youtube(obj, video_url: str, name: str | None):
    """Download a video from YouTube."""
    if not validate_url(video_url):
        click.echo(f"Error: Invalid URL: {video_url}", err=True)
        raise SystemExit(1)
    verbose = obj.get("verbose", False)
    config = get_config()

    # Ensure directories exist
    if temp_path := config.get("temp_path"):
        ensure_dir(temp_path)
    if home_path := config.get("home_path"):
        ensure_dir(home_path)

    if name is None:
        # Get title and upload_date from info command
        info_cmd = build_base_cmd(config, video_url)
        info_cmd.extend(["--dump-json", video_url])
        result = subprocess.run(info_cmd, capture_output=True, text=True)
        if result.stdout:
            data = json.loads(result.stdout)
            upload_date = data.get("upload_date", "unknown")
            title = data.get("title", "video")
            name = f"{upload_date}_{sanitize_filename(title)}"
        else:
            name = "video"

    cmd = build_base_cmd(config, video_url)

    # Output template: home_path/name/name.mp4
    output_template = f"{name}/{name}.%(ext)s"
    cmd.extend(["-o", output_template])

    # Path options
    if temp_path := config.get("temp_path"):
        cmd.extend(["-P", f"temp:{temp_path}"])
    if home_path := config.get("home_path"):
        cmd.extend(["-P", f"home:{home_path}"])

    # Format
    fmt = config.get("format", "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv+ba/b")
    cmd.extend(["-f", fmt])

    # Force output to mp4
    cmd.extend(["--merge-output-format", "mp4"])

    cmd.append(video_url)

    if verbose:
        click.echo(" ".join(cmd))
    result = subprocess.run(cmd)

    # Print final video path on success
    if result.returncode == 0:
        home_path = config.get("home_path", "")
        final_path = Path(home_path) / name / f"{name}.mp4"
        if final_path.exists():
            click.echo(f"Video saved to: {final_path}")
        else:
            click.echo(f"Error: Video file not found at {final_path}", err=True)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
