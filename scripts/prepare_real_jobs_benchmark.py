"""Build a wholly fictional fixture and snapshot 30 employer-published jobs.

This script never opens a personal career file. Run from the repository root.
The fixture is intentionally a general backend/full-stack engineer, not a match
for every specialist role. All employers, dates and accomplishments in its
career history are fictional, including the simulated IBM employment.
"""

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import yaml

from sharp.career import validate_career
from sharp.contracts import Career, Settings

ROOT = Path(__file__).resolve().parents[1] / "outputs/real-jobs-30"
SOURCES = ROOT / "sources"


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value):
    parser = PlainText()
    parser.feed(html.unescape(value))
    lines = []
    for line in "".join(parser.parts).splitlines():
        if any(marker in line for marker in ("â€", "â„", "Ã", "Â")):
            for encoding in ("cp1252", "latin1"):
                try:
                    line = line.encode(encoding).decode("utf-8")
                    break
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json", by_alias=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def profile():
    # Fixed before any selector run. No profile content is read from elsewhere.
    work = [
        ("harbor", "Harborline Commerce", "Senior Software Engineer", "2023-06", None),
        ("pine", "Pinecrest Freight Systems", "Software Engineer II", "2020-03", "2023-05"),
        ("ibm", "IBM", "Software Engineer", "2018-01", "2020-02"),
        ("alder", "Aldercrest Digital", "Junior Software Engineer", "2017-06", "2017-12"),
        ("cedar", "Cedarpoint Health Systems", "Software Engineering Intern", "2016-06", "2016-08"),
        ("north", "Northgate Learning Studio", "Web Development Intern", "2015-06", "2015-08"),
    ]
    groups = {
        "harbor": [
            (
                "payments",
                "Designed Java/Spring Boot payment reconciliation services processing 180,000 daily events; added idempotency keys and replay protection to prevent duplicate ledger entries.",
                "java spring postgres kafka distributed testing",
            ),
            (
                "api_latency",
                "Reduced checkout API p95 latency from 420 to 260 ms by tracing slow PostgreSQL queries, adding targeted indexes, and moving repeated lookups into Redis.",
                "java postgres redis otel performance",
            ),
            (
                "merchant_ui",
                "Led a three-engineer React/TypeScript merchant dashboard redesign with product and support; reduced support requests about settlement status by 24% over the next quarter.",
                "react typescript collaboration leadership",
            ),
            (
                "accessibility",
                "Added keyboard navigation, focus management, and accessible form errors to merchant onboarding; introduced axe checks in Playwright regression tests.",
                "react typescript accessibility playwright testing",
            ),
            (
                "event_delivery",
                "Designed Kafka retry and dead-letter handling for order events, documenting ordering and delivery guarantees and adding safe replay tools for support engineers.",
                "kafka distributed reliability documentation",
            ),
            (
                "observability",
                "Instrumented six backend services with OpenTelemetry and Prometheus; created Grafana dashboards and runbooks that reduced median incident diagnosis from 42 to 27 minutes.",
                "otel prometheus grafana reliability documentation",
            ),
            (
                "identity",
                "Integrated OIDC single sign-on and tenant-scoped authorization for business accounts; added audit events and negative permission tests with the security team.",
                "oidc security testing collaboration java",
            ),
            (
                "mentoring",
                "Mentored two engineers through design reviews and on-call onboarding; introduced short architecture decision records for cross-team API changes.",
                "leadership documentation collaboration architecture",
            ),
            (
                "sdk",
                "Published a versioned TypeScript client SDK from OpenAPI contracts, adding compatibility tests and migration examples for four internal application teams.",
                "typescript openapi testing documentation developer_experience",
            ),
            (
                "delivery",
                "Led a phased Java service migration with feature flags, canary releases, and rollback rehearsals; moved five services without a customer-visible outage during the migration.",
                "java cicd kubernetes reliability architecture",
            ),
            (
                "search",
                "Built OpenSearch-backed merchant order search with filtered queries and pagination; worked with support staff to validate relevance against 120 recurring lookup tasks.",
                "opensearch java search collaboration",
            ),
            (
                "privacy",
                "Implemented retention jobs and export/delete workflows for customer records, with audit logs and legal-reviewed retention rules across three application databases.",
                "postgres privacy security python",
            ),
        ],
        "pine": [
            (
                "tracking",
                "Developed Go/gRPC shipment-tracking services handling 35,000 updates per minute at peak; added backpressure and bounded retries for unreliable carrier feeds.",
                "go grpc distributed reliability",
            ),
            (
                "streaming",
                "Built Kafka ingestion with schema validation and deduplication for 14 carrier feeds; added replayable S3 archives and dashboards for delayed or malformed events.",
                "kafka aws s3 data_engineering testing",
            ),
            (
                "analytics",
                "Built Python/SQL ingestion into a warehouse for shipment-delay analysis; introduced data-quality checks and cut daily dataset preparation from 75 to 25 minutes.",
                "python sql data_engineering analytics",
            ),
            (
                "kubernetes",
                "Containerized four services with Docker and deployed them to Kubernetes using Terraform-managed AWS infrastructure; documented resource limits and deployment recovery.",
                "docker kubernetes terraform aws documentation",
            ),
            (
                "ci",
                "Cut CI feedback from 18 to 7 minutes by separating unit and integration suites and reusing dependency artifacts in GitHub Actions.",
                "cicd testing git developer_experience",
            ),
            (
                "contracts",
                "Introduced REST/gRPC contract tests and synthetic carrier fixtures, catching incompatible payload changes before release across three partner integrations.",
                "grpc rest testing python",
            ),
            (
                "oncall",
                "Rotated primary on-call for shipment services; investigated queue lag and database saturation, wrote incident reviews, and added actionable SLO-based alerts.",
                "reliability prometheus postgres documentation",
            ),
            (
                "frontend",
                "Shipped a React operations map with live shipment updates over WebSockets, working with dispatchers to make late shipments easier to locate.",
                "react typescript websocket collaboration",
            ),
            (
                "database",
                "Partitioned growing PostgreSQL event tables and introduced scheduled archival; reduced a key reporting query from 11 to 3 seconds on the team's load-test dataset.",
                "postgres sql performance data_engineering",
            ),
            (
                "roadmap",
                "Partnered with operations leads to prioritize a quarterly integration roadmap, splitting large carrier requests into independently releasable API changes.",
                "collaboration architecture rest",
            ),
        ],
        "ibm": [
            (
                "enterprise",
                "Developed Java/Spring REST APIs for an enterprise service-management application, implementing request validation, pagination, and structured error responses.",
                "java spring rest testing",
            ),
            (
                "migration",
                "Migrated two scheduled batch jobs to Python services with PostgreSQL checkpoints, reducing duplicate processing and making failed batches restartable.",
                "python postgres reliability",
            ),
            (
                "tests",
                "Added JUnit integration tests and API regression checks to Jenkins builds; reproduced and fixed race conditions in concurrent update flows.",
                "java testing cicd distributed",
            ),
            (
                "support",
                "Investigated production defects with application-support teams, adding structured logs and practical troubleshooting notes for recurring issues.",
                "documentation collaboration reliability",
            ),
            (
                "auth",
                "Integrated an existing OAuth2 provider into internal APIs and tested expired-token and unauthorized-access behavior.",
                "security oidc java testing",
            ),
            (
                "docker",
                "Maintained Docker development environments and Maven dependency upgrades, helping new developers reproduce service behavior locally.",
                "docker java developer_experience git",
            ),
        ],
        "alder": [
            (
                "web",
                "Built responsive React pages and Node.js REST endpoints for two small-business websites, translating designer mockups into tested reusable components.",
                "react javascript node rest testing",
            ),
            (
                "sql",
                "Implemented SQL reporting queries and CSV exports for an appointment-booking application, validating results against the existing spreadsheet process.",
                "sql postgres analytics testing",
            ),
            (
                "quality",
                "Fixed cross-browser layout and form-validation defects and added Jest tests for shared JavaScript utilities.",
                "javascript testing accessibility",
            ),
        ],
    }
    groups["cedar"] = [
        (
            "imports",
            "Built Python validation scripts for appointment-data imports; flagged missing identifiers and duplicate rows before loading staging tables in PostgreSQL.",
            "python postgres testing data_engineering",
        ),
        (
            "reports",
            "Created SQL reports for clinic operations staff and documented reconciliation checks against weekly CSV exports.",
            "sql analytics documentation collaboration",
        ),
    ]
    groups["north"] = [
        (
            "enrollment",
            "Developed JavaScript enrollment forms and Node.js endpoints for a tutoring center; added server-side validation and clear field-level error messages.",
            "javascript node rest testing",
        ),
        (
            "usability",
            "Worked with instructors to simplify lesson scheduling on mobile screens and tested keyboard navigation across the revised pages.",
            "javascript accessibility collaboration",
        ),
    ]
    project_rows = [
        (
            "incident_assistant",
            "Incident-summary prototype",
            "Built a Python prototype that drafts incident summaries from redacted logs using an LLM API; evaluated factual consistency on 40 synthetic incidents and required human review before use.",
            "python llm evaluation privacy",
        ),
        (
            "support_classifier",
            "Support-ticket routing experiment",
            "Compared TF-IDF/logistic regression with sentence embeddings for routing synthetic support tickets; reached macro-F1 0.84 on a held-out 800-ticket test set.",
            "python sklearn embeddings evaluation analytics",
        ),
        (
            "feature_store",
            "Feature snapshot service",
            "Built a small Python feature snapshot service with Parquet/DuckDB datasets and timestamp-based joins to demonstrate reproducible offline training data.",
            "python data_engineering sql testing",
        ),
        (
            "vector_playground",
            "Semantic-search experiment",
            "Built a local semantic-search demo for a public book catalog using sentence-transformer embeddings and pgvector; compared retrieval quality against PostgreSQL full-text search on 60 hand-labeled queries.",
            "python embeddings vector search evaluation postgres",
        ),
        (
            "load_lab",
            "Queue-behavior load lab",
            "Created a Go load generator to compare queue backpressure and retry policies; published reproducible latency and throughput plots with Docker Compose examples.",
            "go distributed performance docker documentation",
        ),
        (
            "flag_service",
            "Feature-flag service",
            "Built a Go feature-flag service with percentage rollouts, tenant targeting, and an audit trail; tested concurrent reads and used Redis for configuration distribution.",
            "go redis testing architecture",
        ),
        (
            "package_checker",
            "Dependency-review tool",
            "Built a TypeScript CLI that checks package license metadata and flags newly introduced dependencies in pull requests; added GitHub Actions integration and fixture-based tests.",
            "typescript node cicd developer_experience testing",
        ),
        (
            "accessibility_kit",
            "Accessible-components study",
            "Created a React component library with keyboard-tested dialogs and forms, Storybook examples, and Playwright accessibility checks for a volunteer community site.",
            "react typescript accessibility playwright testing",
        ),
        (
            "collab_notes",
            "Shared meeting notes",
            "Built a small collaborative notes app using React, Node.js, and WebSockets; implemented reconnect handling and optimistic edits for a five-person study group.",
            "react node websocket typescript",
        ),
        (
            "calendar_api",
            "Calendar-integration service",
            "Built a Node.js scheduling integration with OAuth2, webhook signature validation, and retries; documented setup and rate-limit behavior for a volunteer organization.",
            "node rest security documentation",
        ),
        (
            "cost_dashboard",
            "Cloud-cost explorer",
            "Built a Python/SQL dashboard over sample AWS billing exports, grouping spending by service and owner and adding budget-threshold notifications.",
            "python sql aws analytics",
        ),
        (
            "game_server",
            "Multiplayer game server",
            "Implemented an experimental Go multiplayer lobby with WebSocket sessions, connection timeouts, and load tests for 300 simulated clients.",
            "go websocket testing distributed",
        ),
        (
            "image_browser",
            "Photo-library experiment",
            "Built a browser photo organizer with React and local IndexedDB storage; added thumbnail virtualization and keyboard navigation for a 5,000-photo test collection.",
            "react javascript accessibility performance",
        ),
        (
            "recipe_app",
            "Recipe planning app",
            "Built a React/Node.js recipe planner with PostgreSQL persistence, ingredient filters, and automated API tests for a small group of friends.",
            "react node postgres rest testing",
        ),
    ]
    skill_names = {
        "java": "Java",
        "spring": "Spring Boot",
        "python": "Python",
        "go": "Go",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "react": "React",
        "node": "Node.js",
        "postgres": "PostgreSQL",
        "sql": "SQL",
        "redis": "Redis",
        "kafka": "Kafka",
        "grpc": "gRPC",
        "rest": "REST APIs",
        "aws": "AWS",
        "s3": "Amazon S3",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "terraform": "Terraform",
        "cicd": "CI/CD",
        "git": "Git",
        "testing": "Automated testing",
        "playwright": "Playwright",
        "accessibility": "Web accessibility",
        "otel": "OpenTelemetry",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "oidc": "OAuth2/OIDC",
        "security": "Application security",
        "privacy": "Data retention and privacy",
        "distributed": "Distributed systems",
        "reliability": "On-call and SLOs",
        "performance": "Performance profiling",
        "documentation": "Technical documentation",
        "leadership": "Mentoring and design reviews",
        "architecture": "Service architecture",
        "collaboration": "Cross-functional delivery",
        "openapi": "OpenAPI",
        "developer_experience": "Developer tooling",
        "opensearch": "OpenSearch",
        "search": "Search relevance",
        "data_engineering": "Data pipelines",
        "analytics": "Data analysis",
        "llm": "LLM integration",
        "evaluation": "Model and retrieval evaluation",
        "sklearn": "scikit-learn",
        "embeddings": "Embeddings",
        "vector": "pgvector",
        "websocket": "WebSockets",
    }
    evidence = [
        dict(
            id="fictional_scenario",
            kind="synthetic_fixture",
            source="Entirely fictional benchmark fixture. Not a real candidate, employment record, or verified performance claim.",
        )
    ]
    bullets = []
    for owner, rows in groups.items():
        for suffix, text, skills in rows:
            bullets.append(
                dict(
                    id=f"{owner}_{suffix}",
                    owner_id=owner,
                    text=text,
                    skill_ids=[f"sk_{s}" for s in skills.split()],
                    evidence_ids=["fictional_scenario"],
                    approval="approved",
                )
            )
    projects = []
    for owner, name, text, skills in project_rows:
        projects.append(dict(x_id=owner, name=name))
        bullets.append(
            dict(
                id=f"pr_{owner}",
                owner_id=owner,
                text=text,
                skill_ids=[f"sk_{s}" for s in skills.split()],
                evidence_ids=["fictional_scenario"],
                approval="approved",
            )
        )
    work_records = []
    for owner, name, position, start, end in work:
        record = dict(x_id=owner, name=name, position=position, startDate=start)
        if end:
            record["endDate"] = end
        work_records.append(record)
    summary_rows = [
        (
            "sum_backend",
            "Software engineer with nine years building and operating backend services, event pipelines, and customer-facing products. Leads practical design decisions, mentors teammates, and follows systems through deployment and on-call support.",
        ),
        (
            "sum_fullstack",
            "Software engineer with nine years across Java/Go services and React/TypeScript applications. Connects customer workflows to reliable APIs, accessible interfaces, and tested production releases.",
        ),
        (
            "sum_platform",
            "Software engineer with nine years improving service reliability, deployment workflows, and data platforms. Builds maintainable distributed services and tools that help application teams ship and diagnose software.",
        ),
        (
            "sum_ai",
            "Software engineer with production backend and data-pipeline experience plus independent experiments in LLM integration, embeddings, and retrieval evaluation. Brings service design, testing, and operational discipline to applied AI work.",
        ),
    ]
    career = Career.model_validate(
        dict(
            basics=dict(
                name="Roran StrongHammer",
                label="Senior Software Engineer",
                email="roran.stronghammer@outlook.com",
                phone="+1 (206) 555-0147",
                location=dict(city="Seattle", region="Washington", countryCode="US"),
                url="https://roranstronghammer.dev",
                profiles=[dict(network="LinkedIn", url="https://www.linkedin.com/in/roran-stronghammer"),
                          dict(network="GitHub", url="https://github.com/roranstronghammer"),
                          dict(network="Portfolio", url="https://roranstronghammer.dev")],
            ),
            work=work_records,
            projects=projects,
            education=[
                dict(
                    institution="Westbridge University",
                    studyType="M.S.",
                    area="Software Engineering",
                    startDate="2019",
                    endDate="2022",
                    courses=["Distributed Systems", "Software Architecture", "Database Systems"],
                ),
                dict(
                    institution="Lakeview Institute of Technology",
                    studyType="B.S.",
                    area="Computer Science",
                    endDate="2017",
                    courses=["Data Structures and Algorithms", "Operating Systems", "Computer Networks"],
                )
            ],
            x_resume=dict(
                bullets=bullets,
                evidence=evidence,
                skills=[
                    dict(
                        id=f"sk_{k}",
                        name=v,
                        evidence_ids=["fictional_scenario"],
                        context="project"
                        if k in {"llm", "embeddings", "vector", "sklearn", "evaluation"}
                        else "work",
                    )
                    for k, v in skill_names.items()
                ],
                summaries=[
                    dict(id=k, text=v, evidence_ids=["fictional_scenario"], approval="approved")
                    for k, v in summary_rows
                ],
            ),
        )
    )
    validate_career(career)
    fixture = ROOT / "fixture"
    fixture.mkdir(parents=True, exist_ok=True)
    data = career.model_dump(mode="json", by_alias=True, exclude_none=True)
    (fixture / "master.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    save(fixture / "career.json", data)
    settings = Settings()
    settings.selection_instructions += " Use ONLY this fictional career and this job. Do not read files, use tools, or infer extra experience. Rank up to 18 genuinely relevant bullets with strongest evidence first; give one short specific reason each. Capture 4-6 key requirements. Select only relevant skills, distinguishing project exposure from professional experience. Specialist gaps are acceptable. No need to force all employers into a page."
    save(fixture / "settings.json", settings)
    save(
        fixture / "inventory.json",
        dict(
            disclosure="Entirely fictional candidate and accomplishments; real job postings. IBM employment is also fictional.",
            candidate="Roran StrongHammer",
            years=9,
            employers=len(work),
            work_bullets=sum(map(len, groups.values())),
            projects=len(project_rows),
            total_bullets=len(bullets),
            skills=len(skill_names),
            summaries=len(summary_rows),
            limitations=[
                "No professional ML model training",
                "No Rust or C++ production experience",
                "No kernel or graphics engineering",
                "No hyperscale ownership claims",
                "No employment history at target companies",
            ],
            career_sha256=hashlib.sha256((fixture / "career.json").read_bytes()).hexdigest(),
        ),
    )


def jobs():
    rows = []

    def add(company, identifier, role, url, body, source_file, location="", source_updated=None):
        if len(body) < 800 or "Job not found." in body:
            raise ValueError(f"Invalid source: {company} {identifier}")
        number = len(rows) + 1
        slug = f"{number:02d}-{company.lower().replace(' ', '-')}-{identifier}"
        path = ROOT / "job_posts" / f"{slug}.txt"
        text = f"Company: {company}\nRole: {role}\nJob ID: {identifier}\nSource: {url}\nLocation: {location}\n\n{body}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        rows.append(
            dict(
                slug=slug,
                company=company,
                id=str(identifier),
                role=role,
                url=url,
                location=location,
                job_path=path.relative_to(ROOT).as_posix(),
                source_snapshot=source_file,
                source_updated_at=source_updated,
                job_sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
        )

    for key, identifier, role in [
        ("google-fullstack", "129511213234037446", "Senior Software Engineer, Full Stack, Core"),
        ("google-cloud", "76443197546341062", "Software Engineer III, Google Distributed Cloud"),
    ]:
        source = SOURCES / f"{key}.html"
        body = plain(source.read_text(encoding="utf-8"))
        body = body[body.index("Minimum qualifications:") :]
        body = body.split("Google is proud to be")[0]
        slug = (
            "senior-software-engineer-full-stack-core"
            if key.endswith("fullstack")
            else "software-engineer-iii-google-distributed-cloud"
        )
        add(
            "Google",
            identifier,
            role,
            f"https://www.google.com/about/careers/applications/jobs/results/{identifier}-{slug}",
            body,
            source.name,
            "Bengaluru, India",
        )
    for key, identifier, role, slug in [
        (
            "amazon-data",
            "10556318",
            "Software Development Engineer II",
            "software-development-engineer-ii",
        ),
        (
            "amazon-video",
            "10432755",
            "Software Development Engineer II, Amazon Prime Video",
            "software-development-engineer-ii-amazon-prime-video",
        ),
    ]:
        source = SOURCES / f"{key}.html"
        body = plain(source.read_text(encoding="utf-8"))
        body = body[body.index("Description") :].split("Amazon is an equal opportunity employer")[0]
        add(
            "Amazon",
            identifier,
            role,
            f"https://www.amazon.jobs/en/jobs/{identifier}/{slug}",
            body,
            source.name,
        )
    source = SOURCES / "apple-distributed.html"
    m = re.search(
        r'window.__staticRouterHydrationData\s*=\s*JSON.parse\(("(?:[^"\\]|\\.)*")\)',
        source.read_text(encoding="utf-8"),
    )
    apple = json.loads(json.loads(m[1]))["loaderData"]["jobDetails"]["jobsData"]
    body = "\n\n".join(
        f"{k}:\n{apple[k]}"
        for k in ["jobSummary", "description", "minimumQualifications", "preferredQualifications"]
    )
    add(
        "Apple",
        "200684861",
        apple["postingTitle"],
        "https://jobs.apple.com/en-us/details/200684861/software-engineer-distributed-systems",
        body,
        source.name,
    )
    choices = {
        "stripe": [7557899, 8260985, 7230670],
        "airbnb": [8257826, 7763610, 8242235],
        "figma": [5790627004, 5691911004, 5551686004],
        "cloudflare": [8080780, 8273693, 8104955],
        "reddit": [8044767, 8147617, 7950520],
        "discord": [8811574002, 8856467002, 8817776002],
        "datadog": [8102624, 8242722, 7993551],
        "pinterest": [5459622, 8213988, 6510646],
        "dropbox": [6330377],
    }
    brands = {
        "airbnb": "Airbnb",
        "cloudflare": "Cloudflare",
        "datadog": "Datadog",
        "pinterest": "Pinterest",
        "dropbox": "Dropbox",
    }
    for board, ids in choices.items():
        feed = json.loads((SOURCES / f"{board}.json").read_text(encoding="utf-8"))
        lookup = {j["id"]: j for j in feed["jobs"]}
        for identifier in ids:
            j = lookup[identifier]
            add(
                brands.get(board, board.title()),
                identifier,
                j["title"],
                j["absolute_url"],
                plain(j["content"]),
                f"{board}.json",
                j.get("location", {}).get("name", ""),
                j.get("updated_at"),
            )
    assert len(rows) == 30
    assert len({(r["company"], r["id"]) for r in rows}) == 30
    save(
        ROOT / "jobs.json",
        dict(
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            source_note="Employer career pages and official Greenhouse public board feeds, downloaded in this session. Availability can change.",
            jobs=rows,
        ),
    )
    print(
        json.dumps(
            dict(jobs=len(rows), companies=sorted({r["company"] for r in rows}), root=str(ROOT))
        )
    )


if __name__ == "__main__":
    profile()
    jobs()
