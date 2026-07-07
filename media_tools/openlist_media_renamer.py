#!/usr/bin/env python3
"""Rename media files in OpenList with movie/TV naming rules.

The script intentionally uses only Python standard library modules so it can run
as a standalone source file:

    python3 openlist_media_renamer.py --env-file .evn

Set DRY_RUN=false in the env file, or pass --apply, to call OpenList write APIs.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import io
import json
import os
import posixpath
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable


DEFAULT_RENAME_THREADS = 2
LIBRARY_ROOT_NAMES = {
    "movie",
    "movies",
    "tv",
    "show",
    "shows",
    "series",
    "download",
    "downloads",
    "recent",
    "recently added",
    "最近接收",
    "电影",
    "影片",
    "电视剧",
    "剧集",
    "国产剧",
    "欧美剧",
    "日韩剧",
    "动漫",
    "动画",
}
DEFAULT_MEDIA_EXTENSIONS = {
    ".avi",
    ".flv",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".rmvb",
    ".ts",
    ".webm",
    ".wmv",
}

DEFAULT_MOVIE_TEMPLATE = (
    "{{title}}{% if year %} ({{year}}){% endif %}/"
    "{{title}}{% if year %}.{{year}}{% endif %}"
    "{% if webSource %}.{{webSource}}{% endif %}"
    "{% if edition %}.{{edition|replace(' ', '.')}}{% endif %}"
    "{% if part %}.{{part}}{% endif %}"
    "{% if videoFormat %}.{{videoFormat|replace('4k', '2160p')}}{% endif %}"
    "{% if hdrFormat %}.{{hdrFormat}}{% elif hdr %}.{{hdr}}{% endif %}"
    "{% if videoCodec %}.{{videoCodec|replace('x264', 'H264')|replace('AVC', 'H264')|replace('H265 10bit', 'H265.10bit')|replace('x265 10bit', 'H265.10bit')|replace('x265', 'H265')|replace('HEVC', 'H265')}}{% endif %}"
    "{% if audioCodec %}.{{audioCodec}}{% endif %}"
    "{% if customization %}-{{customization}}{% endif %}"
    "{% if releaseGroup %}-{{releaseGroup}}{% endif %}{{fileExt}}"
)
DEFAULT_TV_TEMPLATE = (
    "{{title}}{% if year %} ({{year}}){% endif %}/Season {{season}}/"
    "{{title}}.{{season_episode}}"
    "{% if videoFormat %}.{{videoFormat|replace('4k', '2160p')}}{% endif %}"
    "{%if webSource %}.{{webSource}}{% endif %}"
    "{% if hdrFormat %}.{{hdrFormat}}{% elif hdr %}.{{hdr}}{% endif %}"
    "{% if edition %}.{{edition|replace(' ', '.')}}{% endif %}"
    "{% if part %}.{{part}}{% endif %}"
    "{% if videoCodec %}.{{videoCodec|replace('x264', 'H264')|replace('AVC', 'H264')|replace('H265 10bit', 'H265.10bit')|replace('x265 10bit', 'H265.10bit')|replace('x265', 'H265')|replace('HEVC', 'H265')}}{% endif %}"
    "{% if audioCodec %}.{{audioCodec}}{% endif %}"
    "{% if customization %}.{{customization}}{% endif %}"
    "{% if releaseGroup %}-{{ releaseGroup }}{% endif %}{{fileExt}}"
)

VIDEO_FORMAT_RE = re.compile(r"(?i)(?:^|[\s._-])(4320p|2160p|4k|1080p|1080i|720p|576p|480p)(?:$|[\s._-])")
YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
TV_SEASON_EP_RE = re.compile(r"(?i)(?:^|[\s._-])S(\d{1,2})[\s._-]*E(\d{1,3}(?:[\s._-]*E\d{1,3})*)(?:$|[\s._-])")
TV_X_EP_RE = re.compile(r"(?i)(?:^|[\s._-])(\d{1,2})x(\d{1,3})(?:$|[\s._-])")
MOVIEPILOT_RELEASE_GROUP_PATTERNS = [
    r"FF(?:(?:A|WE)B|CD|E(?:DU|B)|TV)",
    r"Audies", r"AD(?:Audio|E(?:book|)|Music|Web)",
    r"BeiTai", r"Bts(?:CHOOL|HD|PAD|TV)", r"Zone", r"CarPT",
    r"CHD(?:Bits|PAD|(?:|HK)TV|WEB|)", r"StBOX", r"OneHD", r"Lee", r"xiaopie",
    r"(?:(?:iNT|(?:HALFC|Mini(?:S|H|FH)D))-|)TLF", r"(?:DG|GBWE)B",
    r"Hares(?:(?:M|T)V|Web|)", r"HDA(?:pad|rea|TV)", r"EPiC",
    r"HDC(?:hina|TV|)", r"k9611", r"tudou", r"iHD",
    r"D(?:ream|BTV)", r"(?:HD|QHstudI)o", r"beAst(?:TV|)",
    r"HDH(?:ome|Pad|TV|WEB|)", r"HDPT(?:Web|)", r"HDS(?:ky|TV|Pad|WEB|)", r"AQLJ",
    r"HHWEB", r"HTPT", r"FRDS", r"Yumi", r"cXcY",
    r"L(?:eague(?:(?:C|H)D|(?:M|T)V|NF|WEB)|HD)", r"i18n", r"CiNT",
    r"MTeam(?:TV|)", r"MPAD", r"MWeb", r"Our(?:Bits|TV)", r"FLTTH", r"Ao", r"PbK", r"MGs",
    r"iLove(?:HD|TV)", r"Panda", r"AilMWeb", r"PiGo(?:NF|(?:H|WE)B)",
    r"PTer(?:DIY|Game|(?:M|T)V|WEB|)", r"PTH(?:Audio|eBook|music|ome|tv|WEB|)",
    r"PTsbao", r"OPS", r"F(?:Fans(?:AIeNcE|BD|D(?:VD|IY)|TV|WEB)|HDMv)", r"SGXT",
    r"PuTao", r"CMCT(?:V|)", r"Shark(?:WEB|DIY|TV|MV|)", r"TTG", r"WiKi", r"NGB",
    r"DoA", r"(?:ARi|ExRE)N",
    r"B(?:MDru|eyondHD|TN)", r"C(?:fandora|trlhd|MRG)", r"DON", r"EVO", r"FLUX",
    r"HONE(?:yG|)", r"N(?:oGroup|T(?:b|G))", r"PandaMoon", r"SMURF",
    r"T(?:EPES|aengoo|rollHD )",
    r"ANi", r"HYSUB", r"KTXP", r"LoliHouse", r"MCE", r"Nekomoe kissaten", r"SweetSub",
    r"MingY", r"(?:Lilith|NC)-Raws", r"织梦字幕组", r"枫叶字幕组", r"猎户手抄部",
    r"喵萌奶茶屋", r"漫猫字幕社", r"霜庭云花Sub", r"北宇治字幕组", r"氢气烤肉架",
    r"云歌字幕组", r"萌樱字幕组", r"极影字幕社", r"悠哈璃羽字幕社", r"❀拨雪寻春❀",
    r"沸羊羊(?:制作|字幕组)", r"(?:桜|樱)都字幕组", r"FROG(?:E|Web|)", r"UB(?:its|WEB|TV)",
]
MOVIEPILOT_RELEASE_GROUP_RE = re.compile(
    r"(?<=[-@\[￡【&])(?:(?:%s))(?=$|[@.\s\]\[】&])" % "|".join(MOVIEPILOT_RELEASE_GROUP_PATTERNS),
    re.I,
)
MOVIEPILOT_STREAMING_PLATFORMS = {
    "AMZN": "Amazon",
    "NF": "Netflix",
    "ATVP": "Apple TV+",
    "IT": "iTunes",
    "DSNP": "Disney+",
    "HMAX": "Max",
    "HULU": "Hulu Networks",
    "PCOK": "Peacock",
    "PMTP": "Paramount+",
    "CR": "Crunchyroll",
    "VIU": "Viu",
    "IQ": "iQIYI",
    "LINETV": "LINE TV",
    "CATCHPLAY": "CATCHPLAY+",
    "CPP": "CATCHPLAY+",
    "HAMI": "Hami Video",
    "HAMIVIDEO": "Hami Video",
    "ROKU": "Roku",
    "VIKI": "Rakuten Viki",
    "PLEX": "Plex",
    "TVING": "TVING",
    "WAVVE": "Wavve",
    "BBC": "BBC",
    "IP": "BBC iPlayer",
    "YT": "YouTube",
    "PLAY": "Google Play",
    "MS": "Microsoft Store",
    "MA": "Movies Anywhere",
    "SHO": "Showtime",
    "STAN": "Stan",
    "NOW": "Now",
    "MUBI": "Mubi",
}


@dataclass
class MediaInfo:
    title: str
    file_ext: str
    year: str = ""
    season: str = ""
    season_episode: str = ""
    web_source: str = ""
    edition: str = ""
    part: str = ""
    video_format: str = ""
    hdr_format: str = ""
    hdr: str = ""
    video_codec: str = ""
    video_bit: str = ""
    audio_codec: str = ""
    customization: str = ""
    release_group: str = ""


@dataclass
class RenamePlan:
    info: MediaInfo
    src_path: str
    target_path: str
    effective_src_path: str
    root_rename_from: str = ""
    root_rename_to: str = ""


class OpenListError(RuntimeError):
    pass


class TMDbError(RuntimeError):
    pass


class OpenListClient:
    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        otp_code: str = "",
        token: str = "",
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.otp_code = otp_code
        self.token = token
        self.timeout = timeout

    def login(self) -> None:
        if self.token:
            return
        if not self.username:
            raise OpenListError("missing OpenList username or token")
        data = self.request(
            "POST",
            "/api/auth/login",
            {
                "username": self.username,
                "password": self.password,
                "otp_code": self.otp_code,
            },
            auth=False,
        )
        token = data.get("token")
        if not token:
            raise OpenListError("OpenList login succeeded but no token was returned")
        self.token = token

    def request(self, method: str, api_path: str, payload: dict[str, Any], auth: bool = True) -> dict[str, Any]:
        url = urllib.parse.urljoin(self.base_url + "/", api_path.lstrip("/"))
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = self.token
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise OpenListError(f"HTTP {exc.code} from {api_path}: {raw}") from exc
        except urllib.error.URLError as exc:
            raise OpenListError(f"request failed for {api_path}: {exc}") from exc

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenListError(f"invalid JSON from {api_path}: {raw[:200]}") from exc

        if result.get("code") != 200:
            message = result.get("message") or result.get("msg") or result
            raise OpenListError(f"OpenList API error from {api_path}: {message}")
        data = result.get("data")
        return data if isinstance(data, dict) else {"value": data}

    def list_dir(self, path: str, refresh: bool = False, per_page: int = 200) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self.request(
                "POST",
                "/api/fs/list",
                {"path": normalize_openlist_path(path), "page": page, "per_page": per_page, "refresh": refresh},
            )
            content = data.get("content") or []
            if not isinstance(content, list):
                raise OpenListError(f"unexpected list response for {path}: content is not a list")
            items.extend(content)
            total = int(data.get("total") or len(items))
            if len(items) >= total or not content:
                return items
            page += 1

    def exists(self, path: str) -> bool:
        try:
            self.request("POST", "/api/fs/get", {"path": normalize_openlist_path(path)}, auth=True)
            return True
        except OpenListError as exc:
            if is_not_found_error(exc):
                return False
            raise

    def mkdirs(
        self,
        path: str,
        known_dirs: set[str] | None = None,
        known_dirs_lock: threading.Lock | None = None,
    ) -> None:
        path = normalize_openlist_path(path)
        if path == "/":
            return
        current = ""
        for part in path.strip("/").split("/"):
            current = normalize_openlist_path(posixpath.join(current, part))
            if known_dirs_lock:
                with known_dirs_lock:
                    if known_dirs is not None and current in known_dirs:
                        continue
            elif known_dirs is not None and current in known_dirs:
                continue
            if self.exists(current):
                if known_dirs_lock:
                    with known_dirs_lock:
                        if known_dirs is not None:
                            known_dirs.add(current)
                elif known_dirs is not None:
                    known_dirs.add(current)
                continue
            try:
                self.request("POST", "/api/fs/mkdir", {"path": current})
            except OpenListError:
                if self.exists(current):
                    if known_dirs_lock:
                        with known_dirs_lock:
                            if known_dirs is not None:
                                known_dirs.add(current)
                    elif known_dirs is not None:
                        known_dirs.add(current)
                    continue
                raise
            if known_dirs_lock:
                with known_dirs_lock:
                    if known_dirs is not None:
                        known_dirs.add(current)
            elif known_dirs is not None:
                known_dirs.add(current)

    def rename(self, path: str, new_name: str, overwrite: bool = False) -> None:
        self.request(
            "POST",
            "/api/fs/rename",
            {"path": normalize_openlist_path(path), "name": new_name, "overwrite": overwrite},
        )

    def move(self, src_dir: str, dst_dir: str, names: list[str], overwrite: bool = False) -> None:
        self.request(
            "POST",
            "/api/fs/move",
            {
                "src_dir": normalize_openlist_path(src_dir),
                "dst_dir": normalize_openlist_path(dst_dir),
                "names": names,
                "overwrite": overwrite,
                "skip_existing": False,
                "merge": False,
            },
        )

    def remove(self, dir_path: str, names: list[str]) -> None:
        self.request(
            "POST",
            "/api/fs/remove",
            {
                "dir": normalize_openlist_path(dir_path),
                "names": names,
            },
        )


class TMDbClient:
    def __init__(
        self,
        bearer_token: str = "",
        api_key: str = "",
        language: str = "zh-CN",
        include_adult: bool = False,
        timeout: int = 30,
    ) -> None:
        self.bearer_token = bearer_token
        self.api_key = api_key
        self.language = language
        self.include_adult = include_adult
        self.timeout = timeout
        self.cache: dict[tuple[str, str, str], tuple[str, str]] = {}

    def enabled(self) -> bool:
        return bool(self.bearer_token or self.api_key)

    def request(self, api_path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.enabled():
            raise TMDbError("missing TMDB_BEARER_TOKEN or TMDB_API_KEY")
        params = dict(params or {})
        params.setdefault("language", self.language)
        if self.api_key:
            params["api_key"] = self.api_key
        query = urllib.parse.urlencode(params)
        url = "https://api.themoviedb.org/3/" + api_path.lstrip("/")
        if query:
            url += "?" + query
        headers = {"Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise TMDbError(f"HTTP {exc.code} from TMDb {api_path}: {raw}") from exc
        except urllib.error.URLError as exc:
            raise TMDbError(f"TMDb request failed for {api_path}: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TMDbError(f"invalid JSON from TMDb {api_path}: {raw[:200]}") from exc
        if not isinstance(data, dict):
            raise TMDbError(f"unexpected TMDb response for {api_path}")
        return data

    def resolve(self, media_type: str, parsed: "MediaInfo") -> tuple[str, str]:
        if not self.enabled():
            return parsed.title, parsed.year
        cache_key = (media_type, parsed.title.lower(), parsed.year)
        if cache_key in self.cache:
            return self.cache[cache_key]

        endpoint = "search/movie" if media_type == "movie" else "search/tv"
        params: dict[str, Any] = {
            "query": parsed.title,
            "include_adult": str(self.include_adult).lower(),
            "page": 1,
        }
        if parsed.year:
            if media_type == "movie":
                params["primary_release_year"] = parsed.year
            else:
                params["first_air_date_year"] = parsed.year
        results = self.request(endpoint, params).get("results") or []
        if not isinstance(results, list) or not results:
            self.cache[cache_key] = (parsed.title, parsed.year)
            return self.cache[cache_key]

        best = max(results, key=lambda item: tmdb_score(media_type, parsed, item if isinstance(item, dict) else {}))
        tmdb_id = best.get("id") if isinstance(best, dict) else None
        if not tmdb_id:
            self.cache[cache_key] = (parsed.title, parsed.year)
            return self.cache[cache_key]

        details_path = f"movie/{tmdb_id}" if media_type == "movie" else f"tv/{tmdb_id}"
        details = self.request(details_path)
        title = details.get("title") if media_type == "movie" else details.get("name")
        original_title = details.get("original_title") if media_type == "movie" else details.get("original_name")
        date_value = details.get("release_date") if media_type == "movie" else details.get("first_air_date")
        year = year_from_date(date_value) or parsed.year
        resolved_title = safe_segment(str(title or original_title or parsed.title))
        self.cache[cache_key] = (resolved_title, year)
        return self.cache[cache_key]

    def resolve_by_id(self, media_type: str, tmdb_id: int, parsed: "MediaInfo") -> tuple[str, str]:
        if not self.enabled() or not tmdb_id:
            return parsed.title, parsed.year
        cache_key = (media_type, str(tmdb_id), "id")
        if cache_key in self.cache:
            return self.cache[cache_key]

        details_path = f"movie/{tmdb_id}" if media_type == "movie" else f"tv/{tmdb_id}"
        details = self.request(details_path)
        title = details.get("title") if media_type == "movie" else details.get("name")
        original_title = details.get("original_title") if media_type == "movie" else details.get("original_name")
        date_value = details.get("release_date") if media_type == "movie" else details.get("first_air_date")
        year = year_from_date(date_value) or parsed.year
        resolved_title = safe_segment(str(title or original_title or parsed.title))
        self.cache[cache_key] = (resolved_title, year)
        return self.cache[cache_key]


def normalize_openlist_path(path: str) -> str:
    path = (path or "/").strip()
    if not path.startswith("/"):
        path = "/" + path
    normalized = posixpath.normpath(path)
    return "/" if normalized == "." else normalized


def join_openlist_path(*parts: str) -> str:
    cleaned = [part.strip("/") for part in parts if part and part != "/"]
    return normalize_openlist_path(posixpath.join("/", *cleaned))


def split_ext(filename: str) -> tuple[str, str]:
    stem, ext = posixpath.splitext(filename)
    return stem, ext


def clean_spaces(value: str) -> str:
    value = re.sub(r"[\._]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ._-")


def safe_segment(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value or "Unknown"


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def dotted(value: str) -> str:
    return re.sub(r"\s+", ".", value.strip())


def extract_release_group(stem: str, custom_groups: list[str] | None = None) -> tuple[str, str]:
    matches = []
    group_re = MOVIEPILOT_RELEASE_GROUP_RE
    if custom_groups:
        custom = "|".join(group for group in custom_groups if group)
        if custom:
            group_re = re.compile(
                r"(?<=[-@\[￡【&])(?:(?:%s)|(?:%s))(?=$|[@.\s\]\[】&])"
                % ("|".join(MOVIEPILOT_RELEASE_GROUP_PATTERNS), custom),
                re.I,
            )
    for match in group_re.finditer(f"{stem} "):
        group = match.group(0)
        if group not in matches:
            matches.append(group)
    release_group = "@".join(matches)
    if not release_group:
        return stem, ""

    cleaned = stem
    for group in sorted(matches, key=len, reverse=True):
        cleaned = re.sub(
            rf"[-@\[￡【&]{re.escape(group)}(?=$|[@.\s\]\[】&])",
            "",
            cleaned,
            flags=re.I,
        )
    return cleaned.strip(" ._-"), release_group


def find_year(text: str) -> str:
    matches = YEAR_RE.findall(text)
    return matches[-1] if matches else ""


def year_from_date(value: Any) -> str:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return value[:4]
    return ""


def normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def tmdb_score(media_type: str, parsed: MediaInfo, item: dict[str, Any]) -> float:
    title = item.get("title") if media_type == "movie" else item.get("name")
    original = item.get("original_title") if media_type == "movie" else item.get("original_name")
    date_value = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
    candidates = [str(value) for value in (title, original) if value]
    if not candidates:
        return 0.0
    query = normalize_for_match(parsed.title)
    title_score = max(difflib.SequenceMatcher(None, query, normalize_for_match(candidate)).ratio() for candidate in candidates)
    if parsed.year and parsed.year == year_from_date(date_value):
        title_score += 0.25
    popularity = item.get("popularity")
    if isinstance(popularity, (int, float)):
        title_score += min(float(popularity), 100.0) / 1000.0
    return title_score


def normalize_video_format(value: str) -> str:
    return "2160p" if value.lower() == "4k" else value


def extract_video_format(text: str) -> str:
    match = VIDEO_FORMAT_RE.search(text)
    return normalize_video_format(match.group(1)) if match else ""


def extract_web_source(text: str) -> str:
    platform = extract_streaming_platform(text)
    if platform:
        return platform
    patterns = [
        (r"(?i)(?:UHD[\s._-]*)?Blu[\s._-]*Ray", "BluRay"),
        (r"(?i)WEB[\s._-]*DL", "WEB-DL"),
        (r"(?i)WEB[\s._-]*Rip", "WEBRip"),
        (r"(?i)\bWEB\b", "WEB"),
        (r"(?i)\bHDTV\b", "HDTV"),
        (r"(?i)\bTVRip\b", "TVRip"),
        (r"(?i)\bDVDRip\b", "DVDRip"),
        (r"(?i)\bDVD\b", "DVD"),
    ]
    for pattern, value in patterns:
        if re.search(pattern, text):
            return value
    return ""


def extract_streaming_platform(text: str) -> str:
    tokens = [token for token in re.split(r"[\s._-]+", text) if token]
    upper_tokens = [token.upper() for token in tokens]
    web_tokens = {"WEB", "DL", "WEBDL", "WEBRIP", "WEB-DL"}
    for index, token in enumerate(upper_tokens):
        platform = MOVIEPILOT_STREAMING_PLATFORMS.get(token)
        if not platform:
            continue
        window = upper_tokens[max(0, index - 2): index + 3]
        if any(item in web_tokens for item in window):
            return platform
    return ""


def extract_hdr(text: str) -> tuple[str, str]:
    has_dv = bool(re.search(r"(?i)\b(?:DoVi|DV|Dolby[\s._-]*Vision)\b", text))
    if re.search(r"(?i)\bHDR10(?:\+|[\s._-]*(?:P|Plus)\b)", text):
        return ("HDR10Plus.DV" if has_dv else "HDR10Plus"), ""
    if re.search(r"(?i)\bHDR10\b", text):
        return ("HDR10.DV" if has_dv else "HDR10"), ""
    if re.search(r"(?i)\bHDR\b", text):
        return ("HDR.DV" if has_dv else ""), ("" if has_dv else "HDR")
    if has_dv:
        return "DV", ""
    if re.search(r"(?i)\bHLG\b", text):
        return "HLG", ""
    return "", ""


def extract_video_codec(text: str) -> str:
    if re.search(r"(?i)\bx265\b|\bH[\s._-]*265\b|\bHEVC\b", text):
        return "H265"
    if re.search(r"(?i)\bx264\b|\bH[\s._-]*264\b|\bAVC\b", text):
        return "H264"
    if re.search(r"(?i)\bAV1\b", text):
        return "AV1"
    return ""


def extract_video_bit(text: str) -> str:
    if re.search(r"(?i)(?:10[\s._-]*bit|Hi10P)", text):
        return "10bit"
    if re.search(r"(?i)8[\s._-]*bit", text):
        return "8bit"
    return ""


def extract_audio_codec(text: str) -> str:
    compact = re.sub(r"[\s_-]+", ".", text)
    checks = [
        (r"(?i)TrueHD(?:\.?Atmos)?", "TrueHD.Atmos" if re.search(r"(?i)Atmos", text) else "TrueHD"),
        (r"(?i)DTS\.?HD\.?MA(?:\.?7\.1|\.?5\.1)?", _first_match_text(compact, r"(?i)DTS\.?HD\.?MA(?:\.?7\.1|\.?5\.1)?")),
        (r"(?i)DDP(?:\.?Atmos)?(?:\.?7\.1|\.?5\.1|\.?2\.0)?(?:\.?Atmos)?", _first_match_text(compact, r"(?i)DDP(?:\.?Atmos)?(?:\.?7\.1|\.?5\.1|\.?2\.0)?(?:\.?Atmos)?")),
        (r"(?i)EAC3(?:\.?7\.1|\.?5\.1|\.?2\.0)?", _first_match_text(compact, r"(?i)EAC3(?:\.?7\.1|\.?5\.1|\.?2\.0)?")),
        (r"(?i)AC3(?:\.?7\.1|\.?5\.1|\.?2\.0)?", _first_match_text(compact, r"(?i)AC3(?:\.?7\.1|\.?5\.1|\.?2\.0)?")),
        (r"(?i)DTS(?:\.?7\.1|\.?5\.1)?", _first_match_text(compact, r"(?i)DTS(?:\.?7\.1|\.?5\.1)?")),
        (r"(?i)AAC(?:\.?7\.1|\.?5\.1|\.?2\.0)?", _first_match_text(compact, r"(?i)AAC(?:\.?7\.1|\.?5\.1|\.?2\.0)?")),
        (r"(?i)FLAC(?:\.?7\.1|\.?5\.1|\.?2\.0)?", _first_match_text(compact, r"(?i)FLAC(?:\.?7\.1|\.?5\.1|\.?2\.0)?")),
    ]
    for pattern, value in checks:
        if value and re.search(pattern, compact):
            return normalize_audio_codec(value)
    return ""


def normalize_audio_codec(value: str) -> str:
    value = value.replace("..", ".").strip(".")
    value = re.sub(r"(?i)^DDP\.?", "DDP ", value)
    value = re.sub(r"(?i)^EAC3\.?", "EAC3 ", value)
    value = re.sub(r"(?i)^AC3\.?", "AC3 ", value)
    value = re.sub(r"(?i)^AAC\.?", "AAC ", value)
    value = re.sub(r"(?i)^FLAC\.?", "FLAC ", value)
    value = re.sub(r"(?i)^TrueHD\.?", "TrueHD ", value)
    value = re.sub(r"(?i)^DTS\.?HD\.?MA\.?", "DTS-HD MA ", value)
    value = re.sub(r"(?i)^DTS\.?", "DTS ", value)
    value = value.replace(".Atmos", " Atmos").replace(".atmos", " Atmos")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _first_match_text(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_edition(text: str) -> str:
    patterns = [
        (r"(?i)Director'?s[\s._-]*Cut", "Directors Cut"),
        (r"(?i)Extended[\s._-]*(?:Cut|Edition)?", "Extended"),
        (r"(?i)Theatrical[\s._-]*(?:Cut|Edition)?", "Theatrical"),
        (r"(?i)Unrated", "Unrated"),
        (r"(?i)IMAX", "IMAX"),
        (r"(?i)Criterion", "Criterion"),
    ]
    for pattern, value in patterns:
        if re.search(pattern, text):
            return value
    return ""


def extract_part(text: str) -> str:
    match = re.search(r"(?i)\b(?:Part|Pt|CD|Disc|Disk)[\s._-]*(\d{1,2})\b", text)
    if not match:
        return ""
    label = re.match(r"(?i)\b(Part|Pt|CD|Disc|Disk)", match.group(0))
    prefix = label.group(1) if label else "Part"
    if prefix.lower() == "pt":
        prefix = "Part"
    return f"{prefix}{match.group(1)}"


def title_from_prefix(prefix: str) -> str:
    prefix = re.sub(r"[\[\](){}]", " ", prefix)
    title = clean_spaces(prefix)
    return safe_segment(title)


def strip_after_known_tokens(text: str) -> str:
    token_re = re.compile(
        r"(?i)(?:^|[\s._-])("
        r"4320p|2160p|4k|1080p|1080i|720p|576p|480p|"
        r"WEB[\s._-]*DL|WEB[\s._-]*Rip|Blu[\s._-]*Ray|HDTV|DVDRip|"
        r"HDR10\+?|DoVi|Dolby[\s._-]*Vision|HDR|"
        r"x264|x265|H[\s._-]*264|H[\s._-]*265|HEVC|AVC|AV1|"
        r"DDP|EAC3|AC3|AAC|DTS|TrueHD|FLAC|REMUX"
        r")(?:$|[\s._-])"
    )
    match = token_re.search(text)
    return text[: match.start()] if match else text


def apply_custom_words(title: str, custom_words: list[str] | None = None) -> str:
    for word in custom_words or []:
        if not word or word.startswith("#"):
            continue
        if " => " in word:
            source, replacement = word.split(" => ", 1)
            title = re.sub(source, replacement, title)
        elif " >> " in word and " <> " in word:
            continue
        else:
            title = re.sub(word, "", title)
    return title


def extract_customization(text: str, customization_words: list[str] | None = None) -> str:
    matches = []
    for word in customization_words or []:
        if not word:
            continue
        for match in re.findall(word, text):
            if isinstance(match, tuple):
                for item in match:
                    if item and item not in matches:
                        matches.append(item)
            elif match and match not in matches:
                matches.append(match)
    if matches:
        return "@".join(matches)
    if re.search(r"(?i)\bREMUX\b", text):
        return "REMUX"
    if re.search(r"(?i)\bPROPER\b", text):
        return "PROPER"
    if re.search(r"(?i)\bREPACK\b", text):
        return "REPACK"
    return ""


def parse_media_info(
    filename: str,
    media_type: str,
    moviepilot_config: dict[str, Any] | None = None,
) -> MediaInfo:
    moviepilot_config = moviepilot_config or {}
    stem, ext = split_ext(filename)
    stem = apply_custom_words(stem, moviepilot_config.get("custom_words"))
    stem_without_group, release_group = extract_release_group(stem, moviepilot_config.get("custom_release_groups"))
    text = stem_without_group

    hdr_format, hdr = extract_hdr(text)
    common = {
        "file_ext": ext,
        "year": find_year(text),
        "web_source": extract_web_source(text),
        "edition": extract_edition(text),
        "part": extract_part(text),
        "video_format": extract_video_format(text),
        "hdr_format": hdr_format,
        "hdr": hdr,
        "video_codec": extract_video_codec(text),
        "video_bit": extract_video_bit(text),
        "audio_codec": extract_audio_codec(text),
        "customization": extract_customization(text, moviepilot_config.get("customization")),
        "release_group": release_group,
    }

    if media_type == "tv":
        season, season_episode, title_prefix = parse_tv_episode(text)
        title_text = title_prefix
        if common["year"]:
            title_text = re.sub(rf"(?<!\d){re.escape(common['year'])}(?!\d).*", "", title_text)
        return MediaInfo(
            title=title_from_prefix(title_text),
            season=season,
            season_episode=season_episode,
            **common,
        )

    title_text = text
    if common["year"]:
        title_text = text[: text.rfind(common["year"])]
    else:
        title_text = strip_after_known_tokens(text)
    return MediaInfo(title=title_from_prefix(title_text), **common)


def detect_media_type(filename: str) -> str:
    stem, _ = split_ext(filename)
    if TV_SEASON_EP_RE.search(stem) or TV_X_EP_RE.search(stem):
        return "tv"
    return "movie"


def parse_title_year_hint(folder_name: str) -> tuple[str, str]:
    text = clean_spaces(folder_name)
    year = find_year(text)
    if year:
        title = text[: text.find(year)].strip(" ._-()（）[]【】")
    else:
        title = strip_after_known_tokens(text)
    title = safe_segment(title)
    if title == "Unknown":
        title = ""
    return title, year


def is_library_root_name(name: str) -> bool:
    normalized = clean_spaces(name).lower()
    return normalized in LIBRARY_ROOT_NAMES


def parse_tv_episode(text: str) -> tuple[str, str, str]:
    match = TV_SEASON_EP_RE.search(text)
    if match:
        season_number = int(match.group(1))
        season = str(season_number)
        season_fmt = f"{season_number:02d}"
        episode_tail = re.sub(r"(?i)[\s._-]*E", "E", match.group(2))
        first_ep, *rest = re.split(r"(?i)E", episode_tail)
        normalized = f"S{season_fmt}E{int(first_ep):02d}"
        for ep in rest:
            if ep:
                normalized += f"E{int(ep):02d}"
        return season, normalized, text[: match.start()]

    match = TV_X_EP_RE.search(text)
    if match:
        season_number = int(match.group(1))
        season = str(season_number)
        season_fmt = f"{season_number:02d}"
        episode = f"{int(match.group(2)):02d}"
        return season, f"S{season_fmt}E{episode}", text[: match.start()]

    return "1", "S01E01", strip_after_known_tokens(text)


def override_tv_season(info: MediaInfo, season_number: int | None) -> None:
    if season_number is None or season_number < 0:
        return
    season_fmt = f"{season_number:02d}"
    info.season = str(season_number)
    match = re.match(r"(?i)S\d{1,2}(E.+)", info.season_episode or "")
    if match:
        info.season_episode = f"S{season_fmt}{match.group(1).upper()}"
    else:
        info.season_episode = f"S{season_fmt}E01"


def media_context(info: MediaInfo, media_type: str) -> dict[str, str]:
    video_codec = tv_video_codec(info) if media_type == "tv" else info.video_codec
    return {
        "title": info.title,
        "year": info.year,
        "season": info.season,
        "season_episode": info.season_episode,
        "videoFormat": info.video_format,
        "webSource": info.web_source,
        "hdrFormat": info.hdr_format,
        "hdr": info.hdr,
        "edition": info.edition,
        "part": info.part,
        "videoCodec": video_codec,
        "videoBit": info.video_bit,
        "audioCodec": info.audio_codec,
        "customization": info.customization,
        "releaseGroup": info.release_group,
        "fileExt": info.file_ext,
    }


def render_media_template(template: str, info: MediaInfo, media_type: str) -> str:
    rendered = render_template(template, media_context(info, media_type))
    parts = [safe_segment(part) for part in rendered.split("/") if part]
    return posixpath.join(*parts) if parts else safe_segment(rendered)


def render_template(template: str, context: dict[str, str]) -> str:
    tokens = re.split(r"({{.*?}}|{%.*?%})", template, flags=re.S)
    output: list[str] = []
    stack: list[dict[str, Any]] = []

    def active() -> bool:
        return all(frame["active"] for frame in stack)

    for token in tokens:
        if not token:
            continue
        if token.startswith("{{") and token.endswith("}}"):
            if active():
                output.append(eval_template_expr(token[2:-2].strip(), context))
            continue
        if token.startswith("{%") and token.endswith("%}"):
            statement = token[2:-2].strip()
            if statement.startswith("if "):
                condition = bool(context.get(statement[3:].strip(), ""))
                parent_active = active()
                stack.append({"parent": parent_active, "active": parent_active and condition, "taken": condition})
            elif statement.startswith("elif "):
                if not stack:
                    raise OpenListError("template elif without if")
                frame = stack[-1]
                condition = bool(context.get(statement[5:].strip(), ""))
                frame["active"] = frame["parent"] and (not frame["taken"]) and condition
                frame["taken"] = frame["taken"] or condition
            elif statement == "else":
                if not stack:
                    raise OpenListError("template else without if")
                frame = stack[-1]
                frame["active"] = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif statement == "endif":
                if not stack:
                    raise OpenListError("template endif without if")
                stack.pop()
            continue
        if active():
            output.append(token)
    if stack:
        raise OpenListError("template has unclosed if block")
    return "".join(output)


def eval_template_expr(expr: str, context: dict[str, str]) -> str:
    parts = [part.strip() for part in expr.split("|")]
    value = str(context.get(parts[0], "") or "")
    for filter_expr in parts[1:]:
        match = re.fullmatch(r"replace\((['\"])(.*?)\1\s*,\s*(['\"])(.*?)\3\)", filter_expr)
        if match:
            value = value.replace(match.group(2), match.group(4))
            continue
        raise OpenListError(f"unsupported template filter: {filter_expr}")
    return value


def format_movie_target(info: MediaInfo, template: str = DEFAULT_MOVIE_TEMPLATE) -> str:
    return render_media_template(template, info, "movie")


def format_tv_target(info: MediaInfo, template: str = DEFAULT_TV_TEMPLATE) -> str:
    return render_media_template(template, info, "tv")


def tv_video_codec(info: MediaInfo) -> str:
    if info.video_codec and info.video_bit == "10bit":
        return f"{info.video_codec}.10bit"
    return info.video_codec


def is_season_dir(path: str) -> bool:
    name = posixpath.basename(normalize_openlist_path(path))
    return bool(re.fullmatch(r"(?i)(?:Season[\s._-]*\d{1,2}|S\d{1,2})", name))


def optional_dot(value: str) -> str:
    return f".{value}" if value else ""


def load_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        lines = list(enumerate(fh, 1))
    index = 0
    while index < len(lines):
        line_no, raw_line = lines[index]
        index += 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "<<EOF" in line and "=" not in line:
            key = line.split("<<EOF", 1)[0].strip()
            if not key:
                raise OpenListError(f"invalid env line {path}:{line_no}: empty heredoc key")
            block: list[str] = []
            while index < len(lines):
                _, block_line = lines[index]
                index += 1
                if block_line.strip() == "EOF":
                    break
                block.append(block_line.rstrip("\n"))
            else:
                raise OpenListError(f"invalid env block {path}:{line_no}: missing EOF")
            values[key] = "\n".join(block).strip()
            continue
        if "=" not in line:
            raise OpenListError(f"invalid env line {path}:{line_no}: missing '='")
        key, value = line.split("=", 1)
        key = key.strip()
        value = strip_env_value(value.strip())
        if not key:
            raise OpenListError(f"invalid env line {path}:{line_no}: empty key")
        values[key] = value
    for key, value in os.environ.items():
        if key.startswith(("OPENLIST_", "TMDB_")) or key in {
            "DRY_RUN",
            "OVERWRITE",
            "REFRESH",
            "RENAME_PATHS",
            "RENAME_RECURSIVE",
            "MOVIEPILOT_MOVIE_TEMPLATE",
            "MOVIEPILOT_TV_TEMPLATE",
            "MOVIEPILOT_CUSTOM_WORDS",
            "MOVIEPILOT_CUSTOM_RELEASE_GROUPS",
            "MOVIEPILOT_CUSTOMIZATION",
            "MOVIE_PATHS",
            "TV_PATHS",
            "MOVIE_DEST_ROOT",
            "TV_DEST_ROOT",
            "MEDIA_EXTENSIONS",
            "RULES_JSON",
        }:
            values[key] = value
    return values


def strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if " #" in value:
        return value.split(" #", 1)[0].rstrip()
    return value


def env_bool(env: dict[str, str], key: str, default: bool) -> bool:
    value = env.get(key)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(env: dict[str, str], key: str, default: int) -> int:
    value = env.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise OpenListError(f"{key} must be an integer") from exc


def env_list(env: dict[str, str], key: str) -> list[str]:
    value = env.get(key, "")
    items: list[str] = []
    for line in value.splitlines() or [value]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.split(","):
            part = part.strip()
            if part and not part.startswith("#"):
                items.append(part)
    return items


def load_config(path: str) -> dict[str, Any]:
    env = load_env_file(path)
    extensions = env_list(env, "MEDIA_EXTENSIONS") or sorted(DEFAULT_MEDIA_EXTENSIONS)
    config: dict[str, Any] = {
        "openlist": {
            "base_url": env.get("OPENLIST_BASE_URL", ""),
            "username": env.get("OPENLIST_USERNAME", ""),
            "password": env.get("OPENLIST_PASSWORD", ""),
            "otp_code": env.get("OPENLIST_OTP_CODE", ""),
            "token": env.get("OPENLIST_TOKEN", ""),
            "timeout": env_int(env, "OPENLIST_TIMEOUT", 30),
        },
        "tmdb": {
            "bearer_token": env.get("TMDB_BEARER_TOKEN", ""),
            "api_key": env.get("TMDB_API_KEY", ""),
            "language": env.get("TMDB_LANGUAGE", "zh-CN"),
            "include_adult": env_bool(env, "TMDB_INCLUDE_ADULT", False),
            "required": env_bool(env, "TMDB_REQUIRED", True),
            "timeout": env_int(env, "TMDB_TIMEOUT", 30),
        },
        "dry_run": env_bool(env, "DRY_RUN", True),
        "overwrite": env_bool(env, "OVERWRITE", False),
        "refresh": env_bool(env, "REFRESH", False),
        "rename_threads": env_int(env, "RENAME_THREADS", DEFAULT_RENAME_THREADS),
        "templates": {
            "movie": env.get("MOVIEPILOT_MOVIE_TEMPLATE") or DEFAULT_MOVIE_TEMPLATE,
            "tv": env.get("MOVIEPILOT_TV_TEMPLATE") or DEFAULT_TV_TEMPLATE,
        },
        "moviepilot": {
            "custom_words": env_list(env, "MOVIEPILOT_CUSTOM_WORDS"),
            "custom_release_groups": env_list(env, "MOVIEPILOT_CUSTOM_RELEASE_GROUPS"),
            "customization": env_list(env, "MOVIEPILOT_CUSTOMIZATION"),
        },
        "rules": load_rules(env, extensions),
    }
    return config


def load_rules(env: dict[str, str], extensions: list[str]) -> list[dict[str, Any]]:
    if env.get("RULES_JSON"):
        try:
            rules = json.loads(env["RULES_JSON"])
        except json.JSONDecodeError as exc:
            raise OpenListError("RULES_JSON is not valid JSON") from exc
        if not isinstance(rules, list):
            raise OpenListError("RULES_JSON must be a JSON array")
        return rules

    rules: list[dict[str, Any]] = []
    for path in env_list(env, "RENAME_PATHS"):
        rules.append(
            {
                "path": path,
                "type": "auto",
                "recursive": env_bool(env, "RENAME_RECURSIVE", True),
                "extensions": extensions,
            }
        )
    if rules:
        return rules

    movie_dest = env.get("MOVIE_DEST_ROOT", "")
    for path in env_list(env, "MOVIE_PATHS"):
        rules.append(
            {
                "path": path,
                "destination_root": movie_dest or path,
                "type": "movie",
                "recursive": env_bool(env, "MOVIE_RECURSIVE", True),
                "extensions": extensions,
            }
        )
    tv_dest = env.get("TV_DEST_ROOT", "")
    for path in env_list(env, "TV_PATHS"):
        rules.append(
            {
                "path": path,
                "destination_root": tv_dest or path,
                "type": "tv",
                "recursive": env_bool(env, "TV_RECURSIVE", True),
                "extensions": extensions,
            }
        )
    return rules


def build_client(config: dict[str, Any]) -> OpenListClient:
    openlist = config.get("openlist") or {}
    base_url = openlist.get("base_url")
    if not base_url:
        raise OpenListError("openlist.base_url is required")
    return OpenListClient(
        base_url=base_url,
        username=openlist.get("username", ""),
        password=openlist.get("password", ""),
        otp_code=openlist.get("otp_code", ""),
        token=openlist.get("token", ""),
        timeout=int(openlist.get("timeout", 30)),
    )


def build_tmdb_client(config: dict[str, Any]) -> TMDbClient:
    tmdb = config.get("tmdb") or {}
    return TMDbClient(
        bearer_token=tmdb.get("bearer_token", ""),
        api_key=tmdb.get("api_key", ""),
        language=tmdb.get("language", "zh-CN"),
        include_adult=bool(tmdb.get("include_adult", False)),
        timeout=int(tmdb.get("timeout", 30)),
    )


def collect_files(
    client: OpenListClient,
    root: str,
    recursive: bool,
    refresh: bool,
    extensions: set[str],
    max_files: int = 0,
) -> list[str]:
    root = normalize_openlist_path(root)
    found: list[str] = []
    stack = [root]
    while stack:
        current = stack.pop()
        for item in client.list_dir(current, refresh=refresh):
            name = item.get("name")
            if not isinstance(name, str) or not name:
                continue
            child_path = join_openlist_path(current, name)
            if item.get("is_dir"):
                if recursive:
                    stack.append(child_path)
                continue
            _, ext = split_ext(name)
            if ext.lower() in extensions:
                found.append(child_path)
                if max_files and len(found) >= max_files:
                    return found
    return found


def plan_for_file(
    src_path: str,
    scan_root: str,
    media_type: str,
    tmdb_client: TMDbClient,
    templates: dict[str, str] | None = None,
    moviepilot_config: dict[str, Any] | None = None,
    tmdb_id: int = 0,
    season_number: int | None = None,
) -> RenamePlan:
    filename = posixpath.basename(src_path)
    if media_type == "auto":
        media_type = detect_media_type(filename)
    info = parse_media_info(filename, media_type, moviepilot_config)
    if media_type == "tv":
        override_tv_season(info, season_number)
    title, year = tmdb_client.resolve_by_id(media_type, tmdb_id, info) if tmdb_id else tmdb_client.resolve(media_type, info)
    info.title = title
    info.year = year
    src_dir = normalize_openlist_path(posixpath.dirname(src_path))
    scan_root = normalize_openlist_path(scan_root)
    src_dir_is_season_dir = False
    media_root = src_dir
    while is_season_dir(media_root):
        src_dir_is_season_dir = True
        parent_root = normalize_openlist_path(posixpath.dirname(media_root))
        if parent_root == media_root:
            break
        media_root = parent_root
    hint_title, hint_year = parse_title_year_hint(posixpath.basename(media_root))
    media_root_is_scan_root = media_root == scan_root
    if src_dir_is_season_dir:
        library_dir = normalize_openlist_path(posixpath.dirname(media_root))
    elif media_root_is_scan_root and not is_library_root_name(posixpath.basename(media_root)):
        library_dir = normalize_openlist_path(posixpath.dirname(media_root))
    elif src_dir == scan_root:
        library_dir = src_dir
    else:
        library_dir = normalize_openlist_path(posixpath.dirname(media_root))
    if not tmdb_id and hint_title and (has_cjk(hint_title) or not info.title or info.title == "Unknown"):
        info.title = hint_title
    if not tmdb_id and hint_year:
        info.year = hint_year

    templates = templates or {"movie": DEFAULT_MOVIE_TEMPLATE, "tv": DEFAULT_TV_TEMPLATE}
    template = templates["tv"] if media_type == "tv" else templates["movie"]
    relative_target = render_media_template(template, info, media_type)
    target_path = join_openlist_path(library_dir, relative_target)
    root_rename_from = ""
    root_rename_to = ""
    target_first_part = relative_target.split("/", 1)[0] if "/" in relative_target else ""
    target_media_root = join_openlist_path(library_dir, target_first_part) if target_first_part else ""
    if media_root != target_media_root and posixpath.dirname(media_root) == library_dir:
        root_rename_from = media_root
        root_rename_to = target_media_root

    effective_src_path = src_path
    if root_rename_from and root_rename_to and src_path.startswith(root_rename_from + "/"):
        effective_src_path = root_rename_to + src_path[len(root_rename_from):]

    return RenamePlan(
        info=info,
        src_path=normalize_openlist_path(src_path),
        target_path=target_path,
        effective_src_path=normalize_openlist_path(effective_src_path),
        root_rename_from=root_rename_from,
        root_rename_to=root_rename_to,
    )


def apply_plan(
    client: OpenListClient,
    src_path: str,
    target_path: str,
    overwrite: bool,
    dry_run: bool,
    known_dirs: set[str] | None = None,
    known_dirs_lock: threading.Lock | None = None,
) -> str:
    src_path = normalize_openlist_path(src_path)
    target_path = normalize_openlist_path(target_path)
    if src_path == target_path:
        return "skip: already named"

    src_dir = normalize_openlist_path(posixpath.dirname(src_path))
    src_name = posixpath.basename(src_path)
    target_dir = normalize_openlist_path(posixpath.dirname(target_path))
    target_name = posixpath.basename(target_path)

    if dry_run:
        return "dry-run"

    current_name = src_name
    if current_name != target_name:
        client.rename(src_path, target_name, overwrite=overwrite)
        if not client.exists(normalize_openlist_path(posixpath.join(src_dir, target_name))):
            raise OpenListError(f"rename verification failed: {src_path} -> {target_name}")
        current_name = target_name

    if target_dir != src_dir:
        client.mkdirs(target_dir, known_dirs=known_dirs, known_dirs_lock=known_dirs_lock)
        client.move(src_dir, target_dir, [current_name], overwrite=overwrite)
    return "renamed"


def is_target_exists_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "已存在" in message or "exist" in message or "20004" in message


def is_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "not found" in message
        or "object not found" in message
        or "no such" in message
        or "不存在" in message
        or "已删除" in message
        or "430004" in message
    )


def prepare_plan_for_batch_move(
    client: OpenListClient,
    src_path: str,
    target_path: str,
    overwrite: bool,
    final_target_path: str = "",
) -> dict[str, Any]:
    src_path = normalize_openlist_path(src_path)
    target_path = normalize_openlist_path(target_path)
    final_target_path = normalize_openlist_path(final_target_path) if final_target_path else ""
    if src_path == target_path:
        if final_target_path and final_target_path != target_path:
            if not client.exists(src_path) and not client.exists(final_target_path):
                raise OpenListError(f"source path not found before root rename: {src_path}")
        return {
            "status": "skip: already named",
            "target_path": target_path,
            "current_name": posixpath.basename(src_path),
            "src_dir": normalize_openlist_path(posixpath.dirname(src_path)),
            "target_dir": normalize_openlist_path(posixpath.dirname(target_path)),
            "needs_move": False,
        }

    src_dir = normalize_openlist_path(posixpath.dirname(src_path))
    src_name = posixpath.basename(src_path)
    target_dir = normalize_openlist_path(posixpath.dirname(target_path))
    target_name = posixpath.basename(target_path)

    current_name = src_name
    if current_name != target_name:
        try:
            client.rename(src_path, target_name, overwrite=overwrite)
            if not client.exists(normalize_openlist_path(posixpath.join(src_dir, target_name))):
                raise OpenListError(f"rename verification failed: {src_path} -> {target_name}")
            current_name = target_name
        except Exception as exc:
            if not overwrite and is_target_exists_error(exc) and client.exists(target_path):
                return {
                    "status": "skip: target exists",
                    "target_path": target_path,
                    "current_name": current_name,
                    "src_dir": src_dir,
                    "target_dir": target_dir,
                    "needs_move": False,
                    "warning": str(exc),
                }
            if is_not_found_error(exc):
                candidate_targets = [target_path]
                if final_target_path and final_target_path != target_path:
                    candidate_targets.append(final_target_path)
                for candidate_target in candidate_targets:
                    if client.exists(candidate_target):
                        return {
                            "status": "skip: already named",
                            "target_path": target_path,
                            "current_name": posixpath.basename(candidate_target),
                            "src_dir": src_dir,
                            "target_dir": target_dir,
                            "needs_move": False,
                            "warning": str(exc),
                        }
            raise

    return {
        "status": "renamed",
        "target_path": target_path,
        "current_name": current_name,
        "src_dir": src_dir,
        "target_dir": target_dir,
        "needs_move": target_dir != src_dir,
    }


def collect_root_rename_pairs(plans: list[RenamePlan]) -> list[tuple[str, str]]:
    root_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    target_by_source: dict[str, str] = {}
    source_by_target: dict[str, str] = {}
    for plan in plans:
        if not plan.root_rename_from or not plan.root_rename_to:
            continue
        pair = (plan.root_rename_from, plan.root_rename_to)
        existing_target = target_by_source.get(plan.root_rename_from)
        if existing_target and existing_target != plan.root_rename_to:
            raise OpenListError(
                f"同一媒体目录存在多个目标命名: {plan.root_rename_from} -> "
                f"{existing_target}, {plan.root_rename_to}; 请指定 TMDb ID 或缩小扫描范围"
            )
        existing_source = source_by_target.get(plan.root_rename_to)
        if existing_source and existing_source != plan.root_rename_from:
            raise OpenListError(
                f"多个媒体目录将重命名为同一目标: {existing_source}, "
                f"{plan.root_rename_from} -> {plan.root_rename_to}; 请缩小扫描范围"
            )
        target_by_source[plan.root_rename_from] = plan.root_rename_to
        source_by_target[plan.root_rename_to] = plan.root_rename_from
        if pair not in seen and pair[0] != pair[1]:
            seen.add(pair)
            root_pairs.append(pair)
    return [
        pair for pair in root_pairs
        if not any(
            pair[0] != other_pair[0] and pair[0].startswith(other_pair[0] + "/")
            for other_pair in root_pairs
        )
    ]


def target_path_before_root_rename(plan: RenamePlan) -> str:
    target_path = normalize_openlist_path(plan.target_path)
    if not plan.root_rename_from or not plan.root_rename_to:
        return target_path
    src_root = normalize_openlist_path(plan.root_rename_from)
    dst_root = normalize_openlist_path(plan.root_rename_to)
    if target_path == dst_root:
        return src_root
    if target_path.startswith(dst_root + "/"):
        return src_root + target_path[len(dst_root):]
    return target_path


def refreshed_dir_names(client: OpenListClient, path: str) -> set[str]:
    return {
        str(item.get("name") or "")
        for item in client.list_dir(normalize_openlist_path(path), refresh=True)
        if isinstance(item, dict) and item.get("name")
    }


def is_same_parent_season_rename(src_dir: str, target_dir: str) -> bool:
    src_dir = normalize_openlist_path(src_dir)
    target_dir = normalize_openlist_path(target_dir)
    return (
        normalize_openlist_path(posixpath.dirname(src_dir)) == normalize_openlist_path(posixpath.dirname(target_dir))
        and is_season_dir(src_dir)
        and is_season_dir(target_dir)
        and posixpath.basename(src_dir) != posixpath.basename(target_dir)
    )


def cleanup_empty_season_dirs(client: OpenListClient, path: str) -> None:
    current = normalize_openlist_path(path)
    while current and current != "/" and is_season_dir(current):
        try:
            if refreshed_dir_names(client, current):
                return
        except Exception:
            return
        parent = normalize_openlist_path(posixpath.dirname(current))
        try:
            client.remove(parent, [posixpath.basename(current)])
        except Exception:
            return
        current = parent


def apply_root_renames(
    client: OpenListClient,
    plans: list[RenamePlan],
    overwrite: bool,
    dry_run: bool,
    should_abort: Callable[[], bool] | None = None,
    progress_callback: Callable[[str, str, str, Exception | None], None] | None = None,
) -> set[tuple[str, str]]:
    root_pairs = collect_root_rename_pairs(plans)

    applied: set[tuple[str, str]] = set()
    for src_root, dst_root in root_pairs:
        if should_abort and should_abort():
            if progress_callback:
                progress_callback(src_root, dst_root, "error", OpenListError("aborted"))
            raise OpenListError("aborted")
        if progress_callback:
            progress_callback(src_root, dst_root, "running", None)
        if dry_run:
            print(f"[dry-run] {src_root} -> {dst_root}")
            if progress_callback:
                progress_callback(src_root, dst_root, "dry-run", None)
            applied.add((src_root, dst_root))
            continue
        try:
            for parent in {normalize_openlist_path(posixpath.dirname(src_root)), normalize_openlist_path(posixpath.dirname(dst_root))}:
                if parent:
                    client.list_dir(parent, refresh=True)
            client.rename(src_root, posixpath.basename(dst_root), overwrite=overwrite)
            if not client.exists(dst_root):
                raise OpenListError(f"root rename verification failed: {src_root} -> {dst_root}")
        except Exception as exc:
            if is_not_found_error(exc) and client.exists(dst_root):
                print(f"[skip: already named] {src_root} -> {dst_root}")
                if progress_callback:
                    progress_callback(src_root, dst_root, "skip: already named", None)
                applied.add((src_root, dst_root))
                continue
            if progress_callback:
                progress_callback(src_root, dst_root, "error", exc)
            raise
        print(f"[root-renamed] {src_root} -> {dst_root}")
        if progress_callback:
            progress_callback(src_root, dst_root, "renamed", None)
        applied.add((src_root, dst_root))
    return applied


def apply_file_plans(
    client: OpenListClient,
    plans: list[RenamePlan],
    overwrite: bool,
    dry_run: bool,
    rename_threads: int,
    should_abort: Callable[[], bool] | None = None,
    progress_callback: Callable[[int, RenamePlan, str, str, Exception | None], None] | None = None,
) -> int:
    def aborted() -> bool:
        return bool(should_abort and should_abort())

    entries = [(plan, target_path_before_root_rename(plan)) for plan in plans]
    results: list[dict[str, Any] | None] = [None] * len(entries)
    worker_count = max(1, int(rename_threads or DEFAULT_RENAME_THREADS))
    known_dirs: set[str] = {"/"}
    known_dirs_lock = threading.Lock()

    prepare_started = time.perf_counter()
    if dry_run:
        for index, (plan, target_path) in enumerate(entries):
            if aborted():
                raise OpenListError("aborted")
            if progress_callback:
                progress_callback(index, plan, "running", target_path, None)
            status = apply_plan(client, plan.src_path, target_path, overwrite, dry_run, known_dirs, known_dirs_lock)
            results[index] = {
                "status": status,
                "target_path": target_path,
                "error": None,
                "needs_move": False,
            }
            if progress_callback:
                progress_callback(index, plan, status, target_path, None)
    elif worker_count == 1 or len(entries) <= 1:
        for index, (plan, target_path) in enumerate(entries):
            if aborted():
                results[index] = {
                    "status": "error",
                    "target_path": target_path,
                    "error": OpenListError("aborted"),
                    "needs_move": False,
                }
                if progress_callback:
                    progress_callback(index, plan, "error", target_path, results[index]["error"])
                continue
            if progress_callback:
                progress_callback(index, plan, "running", target_path, None)
            try:
                item = prepare_plan_for_batch_move(client, plan.src_path, target_path, overwrite, plan.target_path)
                item["error"] = None
                results[index] = item
                if progress_callback and (not item.get("needs_move") or item.get("status") != "renamed"):
                    progress_callback(index, plan, item["status"], target_path, None)
            except Exception as exc:
                results[index] = {
                    "status": "error",
                    "target_path": target_path,
                    "error": exc,
                    "needs_move": False,
                }
                if progress_callback:
                    progress_callback(index, plan, "error", target_path, exc)
    else:
        def prepare_with_abort(index: int, plan: RenamePlan, target_path: str) -> dict[str, Any]:
            if aborted():
                raise OpenListError("aborted")
            if progress_callback:
                progress_callback(index, plan, "running", target_path, None)
            return prepare_plan_for_batch_move(client, plan.src_path, target_path, overwrite, plan.target_path)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(
                    prepare_with_abort,
                    index,
                    plan,
                    target_path,
                ): (index, target_path)
                for index, (plan, target_path) in enumerate(entries)
            }
            for future in as_completed(future_map):
                if aborted():
                    for pending in future_map:
                        pending.cancel()
                index, target_path = future_map[future]
                try:
                    item = future.result()
                    item["error"] = None
                    results[index] = item
                    if progress_callback and (not item.get("needs_move") or item.get("status") != "renamed"):
                        progress_callback(index, plans[index], item["status"], target_path, None)
                except Exception as exc:
                    results[index] = {
                        "status": "error",
                        "target_path": target_path,
                        "error": exc,
                        "needs_move": False,
                    }
                    if progress_callback:
                        progress_callback(index, plans[index], "error", target_path, exc)
    print(f"[timing] file_prepare={time.perf_counter() - prepare_started:.2f}s files={len(entries)} threads={worker_count}")

    move_groups: dict[tuple[str, str], list[tuple[int, str]]] = {}
    if not dry_run:
        for index, result in enumerate(results):
            if not result or result.get("error") or not result.get("needs_move"):
                continue
            key = (result["src_dir"], result["target_dir"])
            move_groups.setdefault(key, []).append((index, result["current_name"]))
        move_started = time.perf_counter()
        moved_files = 0
        for (src_dir, target_dir), group_entries in move_groups.items():
            if aborted():
                for index, _ in group_entries:
                    if results[index]:
                        results[index]["status"] = "error"
                        results[index]["error"] = OpenListError("aborted")
                    if progress_callback:
                        progress_callback(index, plans[index], "error", entries[index][1], OpenListError("aborted"))
                continue
            try:
                if is_same_parent_season_rename(src_dir, target_dir) and not client.exists(target_dir):
                    client.rename(src_dir, posixpath.basename(target_dir), overwrite=overwrite)
                    if not client.exists(target_dir):
                        raise OpenListError(f"season directory rename verification failed: {src_dir} -> {target_dir}")
                else:
                    client.mkdirs(target_dir, known_dirs=known_dirs, known_dirs_lock=known_dirs_lock)
                    client.move(src_dir, target_dir, [name for _, name in group_entries], overwrite=overwrite)
                    cleanup_empty_season_dirs(client, src_dir)
                moved_files += len(group_entries)
                if progress_callback:
                    for index, _ in group_entries:
                        progress_callback(
                            index,
                            plans[index],
                            results[index]["status"] if results[index] else "renamed",
                            results[index]["target_path"] if results[index] else entries[index][1],
                            None,
                        )
            except Exception as exc:
                move_error = exc
                try:
                    target_names = refreshed_dir_names(client, target_dir)
                except Exception:
                    target_names = set()
                try:
                    source_names = refreshed_dir_names(client, src_dir)
                except Exception:
                    source_names = set()
                for index, _ in group_entries:
                    result = results[index]
                    current_name = str(result.get("current_name") or "") if result else ""
                    target_path = result["target_path"] if result else entries[index][1]
                    if current_name and current_name in target_names:
                        if result:
                            result["status"] = "renamed"
                            result["error"] = None
                            result["needs_move"] = False
                        moved_files += 1
                        if progress_callback:
                            progress_callback(index, plans[index], "renamed", target_path, None)
                        continue
                    if current_name and current_name in source_names:
                        try:
                            client.move(src_dir, target_dir, [current_name], overwrite=overwrite)
                            if result:
                                result["status"] = "renamed"
                                result["error"] = None
                                result["needs_move"] = False
                            moved_files += 1
                            if progress_callback:
                                progress_callback(index, plans[index], "renamed", target_path, None)
                            continue
                        except Exception as retry_exc:
                            try:
                                target_names = refreshed_dir_names(client, target_dir)
                            except Exception:
                                target_names = set()
                            if current_name in target_names:
                                if result:
                                    result["status"] = "renamed"
                                    result["error"] = None
                                    result["needs_move"] = False
                                moved_files += 1
                                if progress_callback:
                                    progress_callback(index, plans[index], "renamed", target_path, None)
                                continue
                            item_error = retry_exc
                        else:
                            item_error = move_error
                    else:
                        item_error = move_error
                    if result:
                        result["status"] = "error"
                        result["error"] = item_error
                    if progress_callback:
                        progress_callback(index, plans[index], "error", target_path, item_error)
                if all(results[index] and not results[index].get("error") for index, _ in group_entries):
                    cleanup_empty_season_dirs(client, src_dir)
        print(
            f"[timing] batch_move={time.perf_counter() - move_started:.2f}s "
            f"groups={len(move_groups)} files={moved_files}"
        )

    changed = 0
    errors: list[Exception] = []
    for plan, result in zip(plans, results):
        if result is None:
            continue
        status = result["status"]
        target_path = result["target_path"]
        error = result.get("error")
        if error:
            errors.append(error)
            print(f"[error] {plan.src_path} -> {target_path}: {error}", file=sys.stderr)
            continue
        if status in {"dry-run", "renamed"} and plan.src_path != target_path:
            changed += 1
        print(f"[{status}] {plan.src_path} -> {target_path}")
        if not plan.info.title or plan.info.title == "Unknown":
            print(f"  warning: weak title parse for {posixpath.basename(plan.src_path)}", file=sys.stderr)

    if errors:
        raise OpenListError(f"{len(errors)} file rename task(s) failed; root rename skipped")
    return changed


def run(config: dict[str, Any], apply_override: bool | None = None, limit: int = 0) -> int:
    dry_run = bool(config.get("dry_run", True))
    if apply_override is True:
        dry_run = False
    elif apply_override is False:
        dry_run = True

    overwrite = bool(config.get("overwrite", False))
    refresh = bool(config.get("refresh", False))
    rename_threads = max(1, int(config.get("rename_threads") or DEFAULT_RENAME_THREADS))
    templates = config.get("templates") or {"movie": DEFAULT_MOVIE_TEMPLATE, "tv": DEFAULT_TV_TEMPLATE}
    moviepilot_config = config.get("moviepilot") or {}
    rules = config.get("rules") or []
    if not isinstance(rules, list) or not rules:
        raise OpenListError("config.rules must contain at least one rule")

    client = build_client(config)
    client.login()
    tmdb_client = build_tmdb_client(config)
    if (config.get("tmdb") or {}).get("required", True) and not tmdb_client.enabled():
        raise TMDbError("TMDB_REQUIRED=true but TMDB_BEARER_TOKEN/TMDB_API_KEY is empty")

    total = 0
    changed = 0
    for rule in rules:
        root = normalize_openlist_path(rule.get("path", ""))
        if root == "/":
            raise OpenListError("refusing to process OpenList root path; set a specific rule.path")
        media_type = (rule.get("type") or rule.get("media_type") or "movie").lower()
        if media_type not in {"movie", "tv", "auto"}:
            raise OpenListError(f"unsupported media type for {root}: {media_type}")
        recursive = bool(rule.get("recursive", True))
        rule_refresh = bool(rule.get("refresh", refresh))
        extensions = {ext.lower() for ext in rule.get("extensions", DEFAULT_MEDIA_EXTENSIONS)}
        tmdb_id = int(rule.get("tmdb_id") or rule.get("tmdbId") or 0)
        season_value = rule.get("season") if "season" in rule else rule.get("seasonNumber")
        season_number = None if season_value is None or season_value == "" else int(season_value)

        collect_started = time.perf_counter()
        files = collect_files(client, root, recursive, rule_refresh, extensions)
        print(f"[timing] collect_files={time.perf_counter() - collect_started:.2f}s files={len(files)} root={root}")
        plans: list[RenamePlan] = []
        plan_started = time.perf_counter()
        for src_path in files:
            if limit and total >= limit:
                break
            total += 1
            plan = plan_for_file(
                src_path,
                root,
                media_type,
                tmdb_client,
                templates,
                moviepilot_config,
                tmdb_id,
                season_number,
            )
            plans.append(plan)
        print(f"[timing] plan={time.perf_counter() - plan_started:.2f}s planned={len(plans)}")

        collect_root_rename_pairs(plans)
        apply_started = time.perf_counter()
        changed += apply_file_plans(client, plans, overwrite, dry_run, rename_threads)
        print(f"[timing] file_apply={time.perf_counter() - apply_started:.2f}s threads={rename_threads}")
        root_started = time.perf_counter()
        apply_root_renames(client, plans, overwrite, dry_run)
        print(f"[timing] root_rename={time.perf_counter() - root_started:.2f}s")

    print(f"processed={total} planned_changes={changed} dry_run={str(dry_run).lower()}")
    return 0


def self_test() -> int:
    class FixedTMDbClient(TMDbClient):
        def resolve_by_id(self, media_type: str, tmdb_id: int, parsed: "MediaInfo") -> tuple[str, str]:
            return "恶缘", "2025"

    movie = parse_media_info(
        "The.Matrix.1999.2160p.UHD.BluRay.REMUX.HDR10.HEVC.TrueHD.Atmos-FGT.mkv",
        "movie",
    )
    assert movie.title == "The Matrix"
    assert movie.year == "1999"
    assert format_movie_target(movie) == (
        "The Matrix (1999)/"
        "The Matrix.1999.BluRay.2160p.HDR10.H265.TrueHD Atmos-REMUX.mkv"
    )
    hdr10p_movie = parse_media_info(
        "The.Furious.2026.2160p.iT.WEB-DL.DDP5.1.Atmos.HDR10P.H.265-HiveWeb.mkv",
        "movie",
    )
    assert hdr10p_movie.hdr_format == "HDR10Plus"
    assert "HDR10Plus" in format_movie_target(hdr10p_movie)

    tv = parse_media_info(
        "Slow.Horses.2022.S03E01.2160p.WEB-DL.DoVi.HDR.HEVC.DDP5.1-GROUP.mkv",
        "tv",
    )
    assert tv.title == "Slow Horses"
    assert tv.year == "2022"
    assert tv.season == "3"
    assert tv.season_episode == "S03E01"
    assert format_tv_target(tv) == (
        "Slow Horses (2022)/Season 3/"
        "Slow Horses.S03E01.2160p.WEB-DL.HDR.DV.H265.DDP 5.1.mkv"
    )

    rules = load_rules(
        {
            "RENAME_PATHS": "/downloads\n/archive",
        },
        [".mkv"],
    )
    assert len(rules) == 2
    assert rules[0]["type"] == "auto"
    assert detect_media_type("Slow.Horses.2022.S03E01.mkv") == "tv"
    assert detect_media_type("The.Matrix.1999.mkv") == "movie"

    tmdb = TMDbClient()
    assert tmdb.resolve("movie", movie) == ("The Matrix", "1999")
    tv_plan = plan_for_file(
        "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/"
        "Karma.S01E01.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv",
        "/115",
        "auto",
        tmdb,
    )
    assert tv_plan.target_path == (
        "/115/恶缘 (2025)/Season 1/"
        "恶缘.S01E01.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv"
    )
    direct_root_plan = plan_for_file(
        "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/"
        "Karma.S01E06.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv",
        "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G",
        "auto",
        tmdb,
    )
    assert direct_root_plan.target_path == (
        "/115/恶缘 (2025)/Season 1/"
        "恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv"
    )
    assert direct_root_plan.root_rename_from == "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G"
    assert direct_root_plan.root_rename_to == "/115/恶缘 (2025)"
    assert direct_root_plan.effective_src_path == (
        "/115/恶缘 (2025)/Karma.S01E06.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv"
    )
    numeric_root_plan = plan_for_file(
        "/115/最近接收/1/Karma.S01E01.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv",
        "/115/最近接收/1",
        "auto",
        FixedTMDbClient(),
        tmdb_id=999,
    )
    assert numeric_root_plan.target_path == (
        "/115/最近接收/恶缘 (2025)/Season 1/"
        "恶缘.S01E01.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv"
    )
    assert numeric_root_plan.root_rename_from == "/115/最近接收/1"
    assert numeric_root_plan.root_rename_to == "/115/最近接收/恶缘 (2025)"

    class RecordingClient:
        def __init__(self) -> None:
            self.calls: list[tuple[Any, ...]] = []

        def rename(self, path: str, new_name: str, overwrite: bool = False) -> None:
            self.calls.append(("rename", path, new_name, overwrite))

        def exists(self, path: str) -> bool:
            return True

        def mkdirs(self, path: str, **_: Any) -> None:
            self.calls.append(("mkdirs", path))

        def list_dir(self, path: str, refresh: bool = False, per_page: int = 200) -> list[dict[str, Any]]:
            self.calls.append(("list_dir", path, refresh, per_page))
            return []

        def move(self, src_dir: str, dst_dir: str, names: list[str], overwrite: bool = False) -> None:
            self.calls.append(("move", src_dir, dst_dir, names, overwrite))

        def remove(self, dir_path: str, names: list[str]) -> None:
            self.calls.append(("remove", dir_path, names))

    pre_root_target_path = target_path_before_root_rename(direct_root_plan)
    assert pre_root_target_path == (
        "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/Season 1/"
        "恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv"
    )
    recording_client = RecordingClient()
    with contextlib.redirect_stdout(io.StringIO()):
        assert apply_file_plans(
            recording_client,
            [direct_root_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=DEFAULT_RENAME_THREADS,
        ) == 1
    assert recording_client.calls == [
        (
            "rename",
            "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/"
            "Karma.S01E06.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv",
            "恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
            False,
        ),
        ("mkdirs", "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/Season 1"),
        (
            "move",
            "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G",
            "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/Season 1",
            ["恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv"],
            False,
        ),
    ]
    second_root_plan = RenamePlan(
        direct_root_plan.info,
        "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/"
        "Karma.S01E05.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv",
        "/115/恶缘 (2025)/Season 1/"
        "恶缘.S01E05.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
        "/115/恶缘 (2025)/"
        "Karma.S01E05.2025.2160p.WEB.P8.DV.HDR.HEVC.DDP5.1.Atmos-老K.mkv",
        direct_root_plan.root_rename_from,
        direct_root_plan.root_rename_to,
    )
    batch_client = RecordingClient()
    with contextlib.redirect_stdout(io.StringIO()):
        assert apply_file_plans(
            batch_client,
            [direct_root_plan, second_root_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=1,
        ) == 2
    batch_moves = [call for call in batch_client.calls if call[0] == "move"]
    assert batch_moves == [
        (
            "move",
            "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G",
            "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G/Season 1",
            [
                "恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
                "恶缘.S01E05.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
            ],
            False,
        )
    ]

    class PartialTimeoutMoveClient(RecordingClient):
        def __init__(self, completed_names: set[str]) -> None:
            super().__init__()
            self.completed_names = completed_names

        def move(self, src_dir: str, dst_dir: str, names: list[str], overwrite: bool = False) -> None:
            self.calls.append(("move", src_dir, dst_dir, names, overwrite))
            raise TimeoutError("timed out")

        def list_dir(self, path: str, refresh: bool = False, per_page: int = 200) -> list[dict[str, Any]]:
            self.calls.append(("list_dir", path, refresh, per_page))
            if path.endswith("/Season 1"):
                return [{"name": name} for name in sorted(self.completed_names)]
            return []

    partial_timeout_client = PartialTimeoutMoveClient({
        "恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
        "恶缘.S01E05.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
    })
    partial_timeout_out = io.StringIO()
    with contextlib.redirect_stdout(partial_timeout_out):
        assert apply_file_plans(
            partial_timeout_client,
            [direct_root_plan, second_root_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=1,
        ) == 2
    assert partial_timeout_out.getvalue().count("[renamed]") == 2

    class SeasonRenameClient(RecordingClient):
        def __init__(self) -> None:
            super().__init__()
            self.season_renamed = False

        def exists(self, path: str) -> bool:
            path = normalize_openlist_path(path)
            if path == "/shows/Karma/Season 0":
                return self.season_renamed
            return True

        def rename(self, path: str, new_name: str, overwrite: bool = False) -> None:
            super().rename(path, new_name, overwrite)
            if normalize_openlist_path(path) == "/shows/Karma/S00" and new_name == "Season 0":
                self.season_renamed = True

    season_rename_plan = RenamePlan(
        MediaInfo("Karma", ".mkv", "2025", "0", "S00E01"),
        "/shows/Karma/S00/old-name.mkv",
        "/shows/Karma/Season 0/Karma.S00E01.mkv",
        "/shows/Karma/S00/old-name.mkv",
        "",
        "",
    )
    season_rename_client = SeasonRenameClient()
    with contextlib.redirect_stdout(io.StringIO()):
        assert apply_file_plans(
            season_rename_client,
            [season_rename_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=1,
        ) == 1
    assert ("rename", "/shows/Karma/S00", "Season 0", False) in season_rename_client.calls
    assert not [call for call in season_rename_client.calls if call[0] == "move"]

    class ConflictClient(RecordingClient):
        def exists(self, path: str) -> bool:
            return path.endswith("恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv")

        def rename(self, path: str, new_name: str, overwrite: bool = False) -> None:
            raise OpenListError("OpenList API error from /api/fs/rename: code: 20004, message: 很抱歉，该目录名称已存在。")

    conflict_client = ConflictClient()
    conflict_out = io.StringIO()
    with contextlib.redirect_stdout(conflict_out):
        assert apply_file_plans(
            conflict_client,
            [direct_root_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=1,
        ) == 0
    assert "[skip: target exists]" in conflict_out.getvalue()

    class MissingSourceClient(RecordingClient):
        def __init__(self, existing_paths: set[str]) -> None:
            super().__init__()
            self.existing_paths = {normalize_openlist_path(path) for path in existing_paths}

        def exists(self, path: str) -> bool:
            return normalize_openlist_path(path) in self.existing_paths

        def rename(self, path: str, new_name: str, overwrite: bool = False) -> None:
            self.calls.append(("rename", path, new_name, overwrite))
            raise OpenListError("OpenList API error from /api/fs/rename: code: 430004, message: 文件（夹）不存在或已删除。")

    missing_source_client = MissingSourceClient({direct_root_plan.target_path, direct_root_plan.root_rename_to})
    missing_source_out = io.StringIO()
    with contextlib.redirect_stdout(missing_source_out):
        assert apply_file_plans(
            missing_source_client,
            [direct_root_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=1,
        ) == 0
    assert "[skip: already named]" in missing_source_out.getvalue()
    with contextlib.redirect_stdout(missing_source_out):
        assert apply_root_renames(
            missing_source_client,
            [direct_root_plan],
            overwrite=False,
            dry_run=False,
        ) == {(direct_root_plan.root_rename_from, direct_root_plan.root_rename_to)}

    unchanged_root_plan = RenamePlan(
        direct_root_plan.info,
        "/115/旧剧名/Season 1/恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
        "/115/恶缘 (2025)/Season 1/恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
        "/115/恶缘 (2025)/Season 1/恶缘.S01E06.2160p.WEB.HDR.DV.H265.DDP 5.1 Atmos.mkv",
        "/115/旧剧名",
        "/115/恶缘 (2025)",
    )
    unchanged_existing_client = MissingSourceClient({target_path_before_root_rename(unchanged_root_plan)})
    with contextlib.redirect_stdout(io.StringIO()):
        assert apply_file_plans(
            unchanged_existing_client,
            [unchanged_root_plan],
            overwrite=False,
            dry_run=False,
            rename_threads=1,
        ) == 0
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            apply_file_plans(
                MissingSourceClient(set()),
                [unchanged_root_plan],
                overwrite=False,
                dry_run=False,
                rename_threads=1,
            )
        raise AssertionError("expected missing unchanged file before root rename to fail")
    except OpenListError as exc:
        assert "root rename skipped" in str(exc)
    with contextlib.redirect_stdout(io.StringIO()):
        apply_root_renames(recording_client, [direct_root_plan], overwrite=False, dry_run=False)
    assert recording_client.calls[-1] == (
        "rename",
        "/115/恶缘 2025 韩国 奈飞 4K.P8.DV.HDR 精修简体中字 单集7G 共43G",
        "恶缘 (2025)",
        False,
    )
    try:
        apply_root_renames(
            recording_client,
            [
                RenamePlan(direct_root_plan.info, "", "", "", "/shows/Mixed", "/shows/Title A (2025)"),
                RenamePlan(direct_root_plan.info, "", "", "", "/shows/Mixed", "/shows/Title B (2025)"),
            ],
            overwrite=False,
            dry_run=True,
        )
        raise AssertionError("expected conflicting source root rename to fail")
    except OpenListError as exc:
        assert "同一媒体目录存在多个目标命名" in str(exc)
    nested_root_plan = RenamePlan(
        direct_root_plan.info,
        "",
        "",
        "",
        direct_root_plan.root_rename_from + "/S00",
        direct_root_plan.root_rename_from + "/乘风破浪的姐姐 (2020)",
    )
    assert collect_root_rename_pairs([nested_root_plan, direct_root_plan]) == [
        (direct_root_plan.root_rename_from, direct_root_plan.root_rename_to)
    ]
    try:
        apply_root_renames(
            recording_client,
            [
                RenamePlan(direct_root_plan.info, "", "", "", "/shows/Title A", "/shows/Merged (2025)"),
                RenamePlan(direct_root_plan.info, "", "", "", "/shows/Title B", "/shows/Merged (2025)"),
            ],
            overwrite=False,
            dry_run=True,
        )
        raise AssertionError("expected conflicting target root rename to fail")
    except OpenListError as exc:
        assert "多个媒体目录将重命名为同一目标" in str(exc)
    release_plan = plan_for_file(
        "/movies/The.Matrix.1999.2160p.UHD.BluRay.HEVC-FLUX.mkv",
        "/movies",
        "auto",
        tmdb,
    )
    assert release_plan.target_path == "/movies/The Matrix (1999)/The Matrix.1999.BluRay.2160p.H265-FLUX.mkv"
    release_info = parse_media_info("Show.S01E01.1080p.WEB.HEVC-FLUX.mkv", "tv")
    assert release_info.release_group == "FLUX"
    existing_season_plan = plan_for_file(
        "/shows/Karma/Season 01/Karma.S01E02.2025.2160p.WEB.HEVC.mkv",
        "/shows",
        "auto",
        tmdb,
    )
    assert existing_season_plan.target_path == "/shows/Karma (2025)/Season 1/Karma.S01E02.2160p.WEB.H265.mkv"
    s00_dir_plan = plan_for_file(
        "/115/最近接收/Older.Sisters.Who.Brave.The.Winds.And.Waves.2020.S07.2160p.WEB-DL.AAC.H.265-HiveWeb/S00/"
        "Older.Sisters.Who.Brave.The.Winds.And.Waves.2020.S00E250.2160p.WEB-DL.AAC.H.265-HiveWeb.mp4",
        "/115/最近接收/Older.Sisters.Who.Brave.The.Winds.And.Waves.2020.S07.2160p.WEB-DL.AAC.H.265-HiveWeb",
        "auto",
        tmdb,
    )
    assert s00_dir_plan.target_path == (
        "/115/最近接收/Older Sisters Who Brave The Winds And Waves (2020)/Season 0/"
        "Older Sisters Who Brave The Winds And Waves.S00E250.2160p.WEB-DL.H265.AAC.mp4"
    )
    nested_s00_dir_plan = plan_for_file(
        "/115/最近接收/乘风破浪的姐姐 (2020)/S00/Season 0/"
        "乘风破浪的姐姐.S00E250.2160p.WEB-DL.H265.AAC.mp4",
        "/115/最近接收/乘风破浪的姐姐 (2020)",
        "auto",
        tmdb,
    )
    assert nested_s00_dir_plan.target_path == (
        "/115/最近接收/乘风破浪的姐姐 (2020)/Season 0/"
        "乘风破浪的姐姐.S00E250.2160p.WEB-DL.H265.AAC.mp4"
    )
    season_dir_plan = plan_for_file(
        "/115/videos/电视剧/国产剧/一念关山 (2023)/Season 1/一念关山 - S01E40 - 第 40 集.mkv",
        "/115/videos/电视剧/国产剧/一念关山 (2023)/Season 1",
        "tv",
        tmdb,
        season_number=0,
    )
    assert season_dir_plan.target_path == (
        "/115/videos/电视剧/国产剧/一念关山 (2023)/Season 0/"
        "一念关山.S00E40.mkv"
    )
    tmdb_id_plan = plan_for_file(
        "/115/videos/电视剧/欧美剧/办公室 (2005)/Season 6/办公室.S06E26.1080p.WEBRip.H265.10bit.mkv",
        "/115/videos/电视剧/欧美剧/办公室 (2005)/Season 6",
        "tv",
        FixedTMDbClient(),
        tmdb_id=233686,
        season_number=3,
    )
    assert tmdb_id_plan.target_path == (
        "/115/videos/电视剧/欧美剧/恶缘 (2025)/Season 3/"
        "恶缘.S03E26.1080p.WEBRip.H265.10bit.mkv"
    )
    print("self-test passed")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename OpenList media files with movie/TV naming templates.")
    parser.add_argument("--env-file", default=".evn", help="dotenv-style variable file; falls back to .env")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="override config and perform OpenList rename/move")
    mode.add_argument("--dry-run", action="store_true", help="override config and only print planned changes")
    parser.add_argument("--limit", type=int, default=0, help="process at most N files")
    parser.add_argument("--self-test", action="store_true", help="run parser/formatter self-test without OpenList")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    apply_override = True if args.apply else False if args.dry_run else None
    try:
        env_file = args.env_file
        if env_file == ".evn" and not os.path.exists(env_file) and os.path.exists(".env"):
            env_file = ".env"
        config = load_config(env_file)
        return run(config, apply_override=apply_override, limit=args.limit)
    except (OSError, json.JSONDecodeError, OpenListError, TMDbError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
