"""Pydantic models: the data contract (SPEC TRD section 5 and 18.1)."""
from typing import List, Literal

from pydantic import BaseModel, Field


class Patient(BaseModel):
    name: str = ''
    age: str = ''
    sex: str = ''


class Vitals(BaseModel):
    bp: str = ''        # e.g. '150/95'
    temp: str = ''      # degrees F as said, e.g. '102'
    spo2: str = ''
    pulse: str = ''
    resp_rate: str = ''
    sugar: str = ''


class RxItem(BaseModel):
    drug: str = ''
    dose: str = ''        # exactly as clinician said, e.g. '50mg'
    frequency: str = ''   # e.g. 'once daily'
    timing: str = ''      # e.g. 'morning, after food'
    duration: str = ''    # e.g. '30 days'


class RedFlag(BaseModel):
    rule_id: str
    title: str
    severity: Literal['urgent', 'warning']
    matched_inputs: List[str]
    action_text: str


# 18.1 additions
class Utterance(BaseModel):
    id: str
    speaker: Literal['clinician', 'patient', 'unknown'] = 'unknown'
    text: str = ''
    start_s: float | None = None   # only if the STT response provides timing
    end_s: float | None = None


class Provenance(BaseModel):
    source_utterance_ids: List[str] = []
    model: str = ''
    prompt_version: str = ''


class ClinicalRecord(BaseModel):
    patient: Patient = Field(default_factory=Patient)
    chief_complaints: List[str] = []
    vitals: Vitals = Field(default_factory=Vitals)
    diagnosis: str = ''
    prescription: List[RxItem] = []
    advice: List[str] = []
    follow_up: str = ''
    language_detected: str = ''
    red_flags: List[RedFlag] = []
    # 18.1 additions
    utterances: List[Utterance] = []
    allergies: List[str] = []
    said: List[str] = []          # facts with a transcript quote (F13)
    inferred: List[str] = []      # AI suggestions, always labeled (F13)
    provenance: dict[str, Provenance] = {}   # keyed by field path (F25)
    signed_off_by: str = ''
    signed_at: str = ''           # set only by /signoff, never by the LLM
    safety_warnings: List[RedFlag] = []      # F24, reuses the RedFlag model
    warnings: List[str] = []                 # visible pipeline warnings, e.g. extraction failed


class SummaryResponse(BaseModel):
    text: str
    language: str
    audio_base64: str    # wav


# Request bodies for the section 6 routes
class StructureRequest(BaseModel):
    transcript: str


class SummaryRequest(BaseModel):
    record: ClinicalRecord
    language: Literal['mr-IN', 'hi-IN', 'en-IN'] = 'mr-IN'


class AlertAudioRequest(BaseModel):
    red_flags: List[RedFlag]
    language: str = 'mr-IN'


class ReferralRequest(BaseModel):
    record: ClinicalRecord
    confirmed: bool = False
