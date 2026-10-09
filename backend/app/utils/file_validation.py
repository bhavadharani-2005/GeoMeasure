import re
import stat
import zipfile
import zlib
from pathlib import Path, PurePosixPath

from app.core.exceptions import (
    InvalidArchiveError,
    InvalidFileTypeError,
    InvalidShapefileError,
)
from app.models.geospatial_file import FileType

EXTENSION_TO_TYPE = {".kml": FileType.KML, ".zip": FileType.SHAPEFILE}
REQUIRED_SHAPEFILE_PARTS = (".shp", ".shx", ".dbf")
# Only these members are ever written to disk; everything else in the archive is ignored.
SHAPEFILE_PARTS = {".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj", ".sbn", ".sbx"}
MAX_ARCHIVE_MEMBERS = 500
COPY_CHUNK_BYTES = 1024 * 1024
MAX_FILENAME_LENGTH = 120
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def detect_file_type(filename: str) -> FileType:
    file_type = EXTENSION_TO_TYPE.get(Path(filename).suffix.lower())
    if file_type is None:
        raise InvalidFileTypeError()
    return file_type


def safe_filename(filename: str) -> str:
    """Strip directories and unusual characters from a client-supplied filename."""
    name = Path(filename.replace("\\", "/")).name
    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    stem = _UNSAFE_FILENAME_CHARS.sub("_", stem).strip("._") or "upload"
    return f"{stem[: MAX_FILENAME_LENGTH - len(suffix)]}{suffix}"


def _is_ignorable(path: PurePosixPath) -> bool:
    return path.parts[0] == "__MACOSX" or path.name.startswith("._")


def _validated_target(info: zipfile.ZipInfo, destination: Path) -> Path | None:
    """Return a safe on-disk target for a member, None to skip it, or raise on traversal."""
    name = info.filename.replace("\\", "/")
    member = PurePosixPath(name)
    if info.is_dir() or _is_ignorable(member):
        return None
    if member.is_absolute() or ".." in member.parts or re.match(r"^[A-Za-z]:", name):
        raise InvalidArchiveError("The ZIP archive contains unsafe file paths.")
    if stat.S_ISLNK(info.external_attr >> 16):
        raise InvalidArchiveError("The ZIP archive contains symbolic links.")
    if info.flag_bits & 0x1:
        raise InvalidArchiveError("Encrypted ZIP archives are not supported.")
    if member.suffix.lower() not in SHAPEFILE_PARTS:
        return None
    target = (destination / member).resolve()
    if not target.is_relative_to(destination.resolve()):
        raise InvalidArchiveError("The ZIP archive contains unsafe file paths.")
    return target


def extract_shapefile(archive_path: Path, destination: Path, max_bytes: int) -> Path:
    """Safely extract the Shapefile components of a ZIP and return the .shp path.

    Guards against path traversal, symlinks, encrypted members, and zip bombs
    (size is enforced while streaming, not trusted from archive headers).
    """
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise InvalidArchiveError() from exc

    with archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise InvalidArchiveError("The ZIP archive contains too many files.")
        extracted_total = 0
        try:
            for info in members:
                target = _validated_target(info, destination)
                if target is None:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as sink:
                    while chunk := source.read(COPY_CHUNK_BYTES):
                        extracted_total += len(chunk)
                        if extracted_total > max_bytes:
                            raise InvalidArchiveError(
                                "The ZIP archive expands beyond the allowed size."
                            )
                        sink.write(chunk)
        except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError) as exc:
            raise InvalidArchiveError("The ZIP archive is corrupted.") from exc

    return find_shapefile(destination)


def find_shapefile(directory: Path) -> Path:
    shp_files = sorted(p for p in directory.rglob("*") if p.suffix.lower() == ".shp")
    if not shp_files:
        raise InvalidShapefileError("The ZIP archive does not contain a .shp file.")
    if len(shp_files) > 1:
        raise InvalidShapefileError(
            "The ZIP archive contains more than one Shapefile; upload them one at a time."
        )
    shp = shp_files[0]
    missing = [
        ext
        for ext in REQUIRED_SHAPEFILE_PARTS
        if not any(p.suffix.lower() == ext for p in shp.parent.glob(f"{shp.stem}.*"))
    ]
    if missing:
        raise InvalidShapefileError(
            f"The Shapefile is incomplete; missing: {', '.join(missing)}."
        )
    return shp
