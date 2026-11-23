from __future__ import annotations

import json
import re
from pathlib import Path
import typer
from rich import print
from .models import VoiceAuthorization, VoiceProfile, VoiceRequest
from .config import load_settings
from .audio import normalize_reference, validate_reference, atomic_json
from .studio import VoiceStudio
from .text_chunker import split_text
from .transcription import Transcriber

app = typer.Typer(no_args_is_help=True, help="VYRO AI Voice Studio — local TTS and audio QA")


@app.command("create-profile")
def create_profile(
    audio: Path = typer.Option(..., "--audio", exists=True, readable=True),
    profile_id: str = typer.Option(..., "--profile-id"),
    transcript: str = typer.Option(..., "--transcript"),
    relationship: str = typer.Option(..., "--relationship", help="self atau authorized_speaker"),
    consent_record_id: str = typer.Option(..., "--consent-record-id"),
    consent_scope: str = typer.Option(..., "--consent-scope"),
    consent_date: str = typer.Option(..., "--consent-date"),
    rights_confirmed: bool = typer.Option(False, "--rights-confirmed", help="Wajib aktif setelah izin diverifikasi oleh pengguna."),
    expiry_date: str | None = typer.Option(None, "--expiry-date"),
):
    if not rights_confirmed:
        raise typer.BadParameter("Gunakan --rights-confirmed hanya jika suara milik sendiri atau izin eksplisit sudah diperoleh.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", profile_id) or ".." in profile_id:
        raise typer.BadParameter("profile-id hanya boleh berisi huruf, angka, titik, garis bawah, dan tanda hubung; tanpa '..'.")
    authorization = VoiceAuthorization(
        rights_confirmed=True, subject_relationship=relationship,
        consent_record_id=consent_record_id, consent_scope=consent_scope,
        consent_date=consent_date, expiry_date=expiry_date,
    )
    settings = load_settings()
    folder = settings.profile_dir / profile_id
    folder.mkdir(parents=True, exist_ok=True)
    normalized = folder / "reference_16k_mono.wav"
    normalize_reference(audio, normalized)
    validate_reference(normalized, settings.max_reference_seconds)
    profile = VoiceProfile(
        profile_id=profile_id, reference_audio_path=normalized.resolve(),
        reference_transcript=transcript, language="id-ID", authorization=authorization,
    )
    manifest = folder / "voice_profile.json"
    atomic_json(manifest, profile.model_dump(mode="json"))
    print(f"[green]Voice profile created:[/green] {manifest}")
    print("Reference sample has been normalized to mono 16 kHz PCM WAV. Keep this profile private.")

@app.command()
def validate(source: Path = typer.Argument(..., exists=True, readable=True)):
    request = VoiceRequest.model_validate_json(source.read_text(encoding="utf-8"))
    profile = VoiceProfile.model_validate_json(request.voice_profile_path.read_text(encoding="utf-8"))
    print(f"[green]Voice request valid:[/green] {request.content_id} | profile={profile.profile_id}")

@app.command()
def synthesize(source: Path = typer.Argument(..., exists=True, readable=True),
               output: Path | None = typer.Option(None, "--output", "-o"),
               scene_voiceovers: bool = typer.Option(False, "--scene-voiceovers")):
    data = json.loads(source.read_text(encoding="utf-8"))
    if scene_voiceovers:
        data["mode"] = "scene_voiceovers"
    request = VoiceRequest.model_validate(data)
    result = VoiceStudio.from_env().synthesize(request)
    if output and len(result.audio_files) == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(result.audio_files[0].audio_path, output)
    print(f"[green]Voice synthesis complete:[/green] {result.content_id}")
    for artifact in result.audio_files:
        print(f"- {artifact.segment_id}: {artifact.audio_path} ({artifact.duration_seconds}s)")
    print(f"[yellow]Human audio review required. Manifest: {result.metadata_path}[/yellow]")

@app.command()
def transcribe(audio: Path = typer.Argument(..., exists=True, readable=True),
               language: str = typer.Option("id", "--language"),
               output: Path | None = typer.Option(None, "--output", "-o")):
    result = Transcriber().transcribe(audio, language=language)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"[green]Transcript saved:[/green] {output}")
    else:
        print(rendered)

if __name__ == "__main__":
    app()
