"""Public contracts. This module owns data validation, never I/O or SDKs."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, populate_by_name=True)


class ConfidenceLevel(Record):
    id: str
    label: str
    definition: str
    order: int


def confidence_defaults() -> list[ConfidenceLevel]:
    descriptions = [
        (
            "very_high",
            "Very high",
            "Deep firsthand knowledge of decisions, tradeoffs, and results; strongly prefer featuring where relevant.",
        ),
        (
            "high",
            "High",
            "Can clearly explain personal contribution and results; prefer prominent use where relevant.",
        ),
        (
            "medium",
            "Medium",
            "Can discuss the work with some preparation; prefer supporting use.",
        ),
        (
            "low",
            "Low",
            "Limited depth or low preference for emphasis; avoid centering unless specifically appropriate.",
        ),
        (
            "unrated",
            "Unrated",
            "No user assessment supplied. Neutral, not low confidence.",
        ),
    ]
    return [
        ConfidenceLevel(id=identifier, label=label, definition=definition, order=number)
        for number, (identifier, label, definition) in enumerate(descriptions)
    ]


class Confidence(Record):
    level: str = "unrated"
    note: str | None = None
    assessed_hash: str | None = None
    definition_hash: str | None = None


class Evidence(Record):
    id: str
    kind: str = "user_attested"
    source: str
    locator: str | None = None
    excerpt: str | None = None


class Variant(Record):
    id: str
    text: str
    qualifiers: list[str] = Field(default_factory=list)


class Bullet(Record):
    id: str
    owner_id: str
    text: str
    kind: str = "achievement"
    evidence_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    qualifiers: list[str] = Field(default_factory=list)
    approval: Literal["approved", "proposed"] = "proposed"
    confidence: Confidence = Field(default_factory=Confidence)
    variants: list[Variant] = Field(default_factory=list)
    context: str | None = None


class Skill(Record):
    id: str
    name: str
    evidence_ids: list[str] = Field(default_factory=list)
    context: Literal["work", "project", "coursework", "user_attested"] = "user_attested"


class Summary(Record):
    id: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    approval: Literal["approved", "proposed"] = "proposed"


class Extension(Record):
    version: Literal[1] = 1
    bullets: list[Bullet] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    summaries: list[Summary] = Field(default_factory=list)
    confidence_levels: list[ConfidenceLevel] = Field(default_factory=confidence_defaults)


class Career(Record):
    """Standard core records retain upstream fields; x_id supplies stable identity."""

    schema_url: str | None = Field(default=None, alias="$schema")
    basics: dict[str, Any]
    work: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    volunteer: list[dict[str, Any]] = Field(default_factory=list)
    certificates: list[dict[str, Any]] = Field(default_factory=list)
    awards: list[dict[str, Any]] = Field(default_factory=list)
    publications: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)
    interests: list[dict[str, Any]] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    x_resume: Extension = Field(default_factory=Extension)


class Style(Record):
    font: str = "Helvetica"
    size: float = Field(default=10, ge=6, le=60)
    leading: float = Field(default=13, ge=6)
    color: str = Field(default="#1A1A1A", pattern=r"^#[0-9a-fA-F]{6}$")
    bold: bool = False
    italic: bool = False
    before: float = Field(default=0, ge=0)
    after: float = Field(default=4, ge=0)
    indent: float = Field(default=0, ge=0)
    marker: str = ""
    marker_offset: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def valid_marker(self):
        if "\n" in self.marker or "\r" in self.marker:
            raise ValueError("List marker must be a single line")
        if self.marker and not 0 < self.marker_offset <= self.indent:
            raise ValueError("List marker_offset must be positive and fit within indent")
        return self


class TextRun(Record):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    style: dict[str, Any] = Field(default_factory=dict)


class Block(Record):
    id: str
    kind: str
    text: str
    style: Style = Field(default_factory=Style)
    runs: list[TextRun] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    url: str | None = None


class Page(Record):
    width: float = Field(default=612, ge=200)
    height: float = Field(default=792, ge=200)
    margins: list[float] = Field(
        default_factory=lambda: [36, 40, 36, 40], min_length=4, max_length=4
    )
    max_pages: Literal[1, 2] = 1
    fill_targets: list[float] = Field(default_factory=lambda: [0.96])

    @model_validator(mode="after")
    def usable(self):
        top, right, bottom, left = self.margins
        if min(self.margins) < 0 or left + right >= self.width or top + bottom >= self.height:
            raise ValueError("Page margins leave no usable area")
        if any(not 0 <= x <= 1 for x in self.fill_targets):
            raise ValueError("Fill targets must be fractions in [0,1]")
        return self


class Constraints(Record):
    required: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    requires: dict[str, list[str]] = Field(default_factory=dict)


class Customization(Record):
    id: str
    name: str
    purpose: str
    version: int = Field(default=1, ge=1)
    enabled: bool = True
    references: list[str] = Field(default_factory=list)
    stage: Literal["selection", "before_layout", "after_layout"]
    source: str


class Settings(Record):
    version: Literal[1] = 1
    page: Page = Field(default_factory=Page)
    styles: dict[str, Style] = Field(
        default_factory=lambda: {
            "body": Style(),
            "name": Style(size=20, leading=24, after=3, bold=True),
            "label": Style(size=10.5, leading=14, before=4, after=3, bold=True, color="#C44B12"),
            "contact": Style(size=9, leading=12, after=2),
            "heading": Style(size=11, leading=14, before=8, after=5, bold=True, color="#C44B12"),
            "owner": Style(size=10.5, leading=14, before=4, after=3, bold=True, color="#1F5A8A"),
            "education": Style(bold=True),
            "bullet": Style(indent=12, marker="•", marker_offset=12),
        }
    )
    exceptions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    section_order: list[str] = Field(
        default_factory=lambda: ["summary", "work", "projects", "education", "skills"]
    )
    experience_first: bool = True
    constraints: Constraints = Field(default_factory=Constraints)
    skills_fill_target: float = Field(default=0.95, ge=0, le=1)
    skills_max_lines: int = Field(default=3, ge=1, le=12)
    selection_instructions: str = "Choose proven relevant function first. Prefer relevant work experience before projects. Preserve ownership, qualifications and evidence. Use user confidence as secondary guidance, not factual certainty."
    customizations: list[Customization] = Field(default_factory=list)


class ChoiceInput(Record):
    contract_version: Literal[1] = 1
    career: Career
    job: str = ""
    instructions: str = ""
    constraints: Constraints = Field(default_factory=Constraints)
    confidence_review: dict[str, bool] = Field(default_factory=dict)


class Decision(Record):
    candidate_id: str
    variant_id: str | None = None
    requirement_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    provider_confidence: Any = None


class ChoicePlan(Record):
    version: Literal[1] = 1
    ranked: list[Decision]
    summary_id: str | None = None
    skill_ids: list[str] = Field(default_factory=list)
    provider: str = "user"
    model: str | None = None
    requirements: dict[str, str] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    provider_version: str | None = None
    raw_response_ref: str | None = None


class Changes(Record):
    patches: dict[str, dict[str, Any]] = Field(default_factory=dict)
    runs: dict[str, list[TextRun]] = Field(default_factory=dict)
    constraints: Constraints | None = None
    reason: str | None = None


class Decorations(Record):
    colors: dict[str, str] = Field(default_factory=dict)
    runs: dict[str, list[TextRun]] = Field(default_factory=dict)
    reason: str | None = None


class Line(Record):
    text: str
    start: int
    end: int
    width: float
    available_width: float


class Measurement(Record):
    block_id: str
    lines: list[Line]
    height: float
    fingerprint: str


class PlacedBlock(Record):
    block: Block
    page: int
    x: float
    y: float
    width: float
    measurement: Measurement


class Layout(Record):
    version: Literal[1] = 1
    placed: list[PlacedBlock]
    pages: int
    selected_ids: list[str] = Field(default_factory=list)
    omitted_ids: list[str] = Field(default_factory=list)
    page_fill: list[float]
    remaining_height: list[float]
    skills_line_fill: float = 0
    issues: list[str] = Field(default_factory=list)


class SelectionPolicyInput(Record):
    contract_version: Literal[1] = 1
    input: ChoiceInput
    plan: ChoicePlan


class BeforeInput(Record):
    contract_version: Literal[1] = 1
    document: list[Block]
    settings: Settings
    career: Career
    job: str = ""
    measurements: list[Measurement] = Field(default_factory=list)


class AfterInput(Record):
    contract_version: Literal[1] = 1
    layout: Layout
    settings: Settings
    career: Career
    job: str = ""


class WriteInput(Record):
    career: Career
    instruction: str
    target_ids: list[str]


class Proposal(Record):
    target_id: str
    text: str
    evidence_ids: list[str]
    qualifiers: list[str]


class ProposedChanges(Record):
    base_hash: str
    changes: list[Proposal]


class CreateRequest(Record):
    document_type: Literal["resume", "cover_letter"] = "resume"
    career_path: str
    settings_path: str
    output_dir: str
    job: str = ""
    formats: list[Literal["pdf", "pptx", "docx"]] = Field(default_factory=lambda: ["pdf"])
    selection_path: str | None = None
    title: str = "Resume"
    letter_text: str | None = None


class Artifact(Record):
    path: str
    format: str
    checks: dict[str, Any] = Field(default_factory=dict)


class RunResult(Record):
    run_id: str
    output_dir: str
    artifacts: list[Artifact]
    layout: Layout
    timings: dict[str, float]


class RunSummary(Record):
    run_id: str
    output_dir: str
    artifacts: list[Artifact]
    pages: int
    selected_ids: list[str]
    omitted_ids: list[str]
    page_fill: list[float]
    skills_line_fill: float
    remaining_height: list[float]
    issues: list[str]
    timings: dict[str, float]


class Chooser(Protocol):
    def choose(self, request: ChoiceInput) -> ChoicePlan: ...


class Writer(Protocol):
    def write(self, request: WriteInput) -> ProposedChanges: ...


class Measurer(Protocol):
    def measure(self, block: Block, width: float) -> Measurement: ...


class Exporter(Protocol):
    def export(self, layout: Layout, settings: Settings, destination: str) -> Artifact: ...


class RuleRunner(Protocol):
    def run(self, customization: Customization, payload: dict[str, Any]) -> dict[str, Any]: ...
