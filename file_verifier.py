import hashlib
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import quote, urlparse, urlunparse

import requests


class FileVerifierError(Exception):
    """Error de verificación o reparación de archivos."""


def calculate_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as file_handler:
        for chunk in iter(lambda: file_handler.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def _build_entry(path: str, metadata: dict) -> Optional[Dict[str, str]]:
    if not path or not isinstance(metadata, dict):
        return None

    expected_hash = (
        metadata.get("sha256")
        or metadata.get("hash")
        or metadata.get("checksum")
        or metadata.get("sha")
    )
    if not expected_hash:
        return None

    return {
        "path": str(path).replace("\\", "/"),
        "sha256": str(expected_hash).lower(),
        "url": metadata.get("url"),
    }


def _normalize_manifest(manifest_data) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []

    # Caso 1: lista directa de entradas
    if isinstance(manifest_data, list):
        for item in manifest_data:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("file") or item.get("name")
            entry = _build_entry(path, item) if path else None
            if entry:
                normalized.append(entry)
        return normalized

    if not isinstance(manifest_data, dict):
        return normalized

    files_data = manifest_data.get("files")

    # Caso 2: {"files": [...]} (lista)
    if isinstance(files_data, list):
        for item in files_data:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("file") or item.get("name")
            entry = _build_entry(path, item) if path else None
            if entry:
                normalized.append(entry)
        return normalized

    # Caso 3: {"files": {"ruta": {"hash": "..."}}}  <-- tu formato
    if isinstance(files_data, dict):
        for path, metadata in files_data.items():
            entry = _build_entry(path, metadata)
            if entry:
                normalized.append(entry)
        return normalized

    # Caso 4: {"entries": [...]} legado
    entries_data = manifest_data.get("entries")
    if isinstance(entries_data, list):
        for item in entries_data:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("file") or item.get("name")
            entry = _build_entry(path, item) if path else None
            if entry:
                normalized.append(entry)

    return normalized


def _build_file_url(path: str, files_base_url: str, custom_url: Optional[str] = None) -> str:
    if custom_url:
        return custom_url

    if not files_base_url:
        raise FileVerifierError("files_base_url no está configurado.")

    encoded_path = quote(path, safe="/-_.")
    parsed = urlparse(files_base_url)

    if not parsed.scheme or not parsed.netloc:
        raise FileVerifierError("files_base_url no es una URL válida.")

    base_path = parsed.path.rstrip("/")
    combined_path = f"{base_path}/{encoded_path}" if base_path else f"/{encoded_path}"

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        combined_path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))


def _download_file(url: str, destination: Path, timeout: int = 60) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_destination = destination.with_suffix(destination.suffix + ".tmp")

    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()

    with temp_destination.open("wb") as file_handler:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file_handler.write(chunk)

    temp_destination.replace(destination)


def verify_and_repair_files(
    manifest_url: str,
    files_base_url: str,
    base_directory: str = ".",
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, object]:
    if not manifest_url:
        raise FileVerifierError("manifest_url no está configurado.")

    def emit_status(message: str):
        if status_callback:
            status_callback(message)

    def emit_progress(current: int, total: int, detail: str):
        if progress_callback:
            progress_callback(current, total, detail)

    emit_status("Descargando manifiesto...")
    response = requests.get(manifest_url, timeout=20)
    response.raise_for_status()
    manifest_data = response.json()

    entries = _normalize_manifest(manifest_data)
    if not entries:
        sample_keys = list(manifest_data.keys()) if isinstance(manifest_data, dict) else []
        raise FileVerifierError(
            "El manifiesto no contiene entradas válidas de archivos. "
            f"Claves detectadas: {sample_keys}"
        )

    root = Path(base_directory).resolve()
    checked = 0
    downloaded = 0
    repaired = 0
    failures = []

    total = len(entries)

    for index, entry in enumerate(entries, start=1):
        relative_path = entry["path"]
        expected_hash = entry["sha256"]
        target_path = (root / relative_path).resolve()

        if root not in target_path.parents and target_path != root:
            failures.append({"path": relative_path, "error": "Ruta fuera del directorio base"})
            emit_progress(index, total, f"{relative_path} - ruta inválida")
            checked += 1
            continue

        needs_download = True
        state = "faltante"

        if target_path.exists() and target_path.is_file():
            current_hash = calculate_sha256(target_path)
            if current_hash.lower() == expected_hash:
                needs_download = False
                state = "ok"
            else:
                state = "corrupto"

        if needs_download:
            try:
                file_url = _build_file_url(relative_path, files_base_url, entry.get("url"))
                emit_status(f"Descargando {relative_path}...")
                _download_file(file_url, target_path)

                downloaded_hash = calculate_sha256(target_path)
                if downloaded_hash.lower() != expected_hash:
                    file_size = target_path.stat().st_size if target_path.exists() else 0
                    raise FileVerifierError(
                        "Hash SHA256 no coincide después de descargar "
                        f"(esperado={expected_hash}, obtenido={downloaded_hash}, bytes={file_size}, url={file_url})"
                    )

                downloaded += 1
                if state == "corrupto":
                    repaired += 1
                state = "reparado" if state == "corrupto" else "descargado"
            except Exception as error:
                failures.append({"path": relative_path, "error": str(error)})
                state = f"error: {error}"

        checked += 1
        emit_progress(index, total, f"{relative_path} [{state}]")

    result = {
        "checked": checked,
        "total": total,
        "downloaded": downloaded,
        "repaired": repaired,
        "failures": failures,
    }

    if failures:
        emit_status(
            f"Verificación finalizada con errores ({len(failures)}). Descargados: {downloaded}."
        )
    else:
        emit_status(
            f"Verificación completada. Descargados/Reparados: {downloaded} (corruptos reparados: {repaired})."
        )

    return result
