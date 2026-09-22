# Engineering Knowledge Format (EKF)

**Version 0.1 - Draft**

## 1. Purpose

Engineering Knowledge Format (EKF) is an open, human-readable and agent-friendly format for representing engineering intent, requirements, architecture, design, interfaces, decisions, risks, verification and evidence.

EKF is designed for an engineering environment where humans and AI agents work together continuously.

The basic model is:

```text
Human intent
     ↓
Engineering agent
     ↕
EKF engineering knowledge graph
     ↕
Models / code / simulation / physical system
     ↕
Verification evidence
```

EKF uses ordinary files stored in version control rather than requiring a proprietary requirements or systems-engineering database.

An EKF repository should be understandable using standard tools such as:

```text
cat
grep
git
Markdown editors
Python
LLM agents
graph tools
CI pipelines
```

EKF is inspired by the Open Knowledge Format (OKF) and follows the same general principles of portability, readability, structured metadata and agent accessibility.

---

# 2. Design principles

EKF follows eight principles.

## 2.1 Engineering knowledge is the source of truth

The primary object is not a requirement record.

The primary object is an **engineering knowledge artifact**.

Examples include:

* intent
* requirement
* constraint
* interface
* architecture
* component
* decision
* assumption
* hazard
* risk
* verification
* evidence

Requirements are one type of engineering knowledge among several.

---

## 2.2 Files are the database

Engineering knowledge SHOULD be stored as UTF-8 Markdown files with YAML frontmatter.

Example:

```text
requirements/emergency-shutdown.md
```

No proprietary database is required.

Derived databases, graph indexes, vector stores and search indexes MAY be generated for performance, but they MUST NOT become the authoritative engineering source.

---

## 2.3 Git provides configuration management

Git SHOULD provide:

* history
* branches
* engineering change proposals
* reviews
* approvals
* baselines
* releases
* rollback
* comparison between system states

An engineering baseline is therefore fundamentally a Git commit.

A Git tag MAY provide a human-readable baseline identifier.

Example:

```text
system-v2.3
```

---

## 2.4 Traceability is a graph, not a matrix

Relationships between artifacts form an engineering knowledge graph.

Traditional traceability matrices SHOULD be generated from this graph when required.

They SHOULD NOT normally be manually maintained.

---

## 2.5 Agents maintain the graph

AI agents MAY:

* create artifacts
* propose changes
* establish relationships
* detect missing relationships
* perform impact analysis
* identify inconsistencies
* propose verification
* analyze test coverage
* update documentation
* create change branches
* review engineering changes

Humans remain responsible for decisions and approvals according to the governance of the engineering organization.

---

## 2.6 Meaning is more important than document structure

EKF does not require engineering knowledge to be decomposed into thousands of atomic requirements unless that decomposition provides engineering value.

A richer engineering artifact may contain:

```text
Intent
Behaviour
Constraints
Interfaces
Rationale
Acceptance criteria
Verification strategy
```

Atomic requirements MAY be produced when needed for contractual, regulatory, safety or organizational reasons.

---

## 2.7 Implementation is part of engineering knowledge

Code, models, simulations, test software and physical test results are not separate from systems engineering.

EKF SHOULD allow engineering intent to be connected directly to implementation and evidence.

---

## 2.8 Agents are tool-using engineering actors

An engineering agent SHOULD NOT be limited to reading and writing text.

It SHOULD be able to use tools such as:

* Git
* compilers
* test frameworks
* simulation tools
* databases
* graph engines
* static analysis tools
* mathematical tools
* CAD or model-processing tools
* APIs
* engineering command-line tools

The agent SHOULD also have access to a generic execution environment, such as a sandboxed command shell.

This allows the agent to create new tools when an appropriate tool does not already exist.

For example, the agent may decide to create a Python program to:

* parse a test result
* compare two signal traces
* calculate a timing margin
* extract information from engineering data
* generate a graph
* validate hundreds of artifacts
* convert between formats
* analyze a large data set
* invoke another engineering tool

The engineering agent is therefore not only a user of predefined tools.

It is capable of **extending its own engineering toolset within controlled boundaries**.

---

# 3. EKF repository

A typical repository might contain:

```text
engineering/
    ekf.yaml
    index.md

    intent/
    requirements/
    constraints/
    architecture/
    interfaces/
    decisions/
    assumptions/
    safety/
    verification/
    evidence/

src/
models/
simulation/
tests/
tools/
```

The directory structure is NOT normative.

Organizations MAY organize artifacts however they prefer.

Artifact identity MUST NOT depend on directory location.

This allows artifacts to move without breaking the engineering graph.

---

# 4. Repository manifest

An EKF repository SHOULD contain:

```text
ekf.yaml
```

Example:

```yaml
ekf: "0.1"

system:
  id: BATTERY-SYSTEM
  title: Industrial Battery System

defaults:
  artifact_format: markdown
  relation_model: ekf
```

Future versions MAY define additional repository-level configuration.

---

# 5. Engineering artifacts

An EKF artifact is a Markdown file containing YAML frontmatter followed by a Markdown body.

Example:

```yaml
---
ekf: "0.1"

id: REQ-HV-014
type: requirement
title: Emergency shutdown

status: stable

relations:
  - type: derives-from
    target: INTENT-SAFE-001

  - type: allocated-to
    target: COMP-CONTACTOR-001

  - type: verified-by
    target: VER-HV-022
---

# Emergency shutdown

The battery shall disconnect its DC output when the emergency
shutdown input is asserted.

## Acceptance criteria

Output current shall fall below 1 A within 250 ms.

## Rationale

Prevents continued energy delivery after an external emergency
shutdown request.
```

---

# 6. Required metadata

Every EKF artifact MUST contain:

```yaml
ekf: "0.1"
id: <stable identifier>
type: <artifact type>
title: <human readable title>
```

Example:

```yaml
ekf: "0.1"
id: REQ-HV-014
type: requirement
title: Emergency shutdown
```

## 6.1 `id`

`id` uniquely identifies the engineering concept.

IDs MUST be unique within an EKF repository.

IDs SHOULD remain stable throughout the lifetime of the concept.

Moving or renaming the file MUST NOT require changing its ID.

## 6.2 `type`

`type` identifies the kind of engineering knowledge represented.

EKF defines a recommended core vocabulary but allows additional types.

Consumers MUST tolerate unknown types.

## 6.3 `title`

`title` provides a concise human-readable name.

---

# 7. Core artifact types

EKF v0.1 defines the following recommended types:

```text
intent
requirement
constraint
interface
architecture
component
decision
assumption
hazard
risk
verification
evidence
```

This list is intentionally small and NOT closed.

Organizations MAY introduce types such as:

```text
cybersecurity-control
regulatory-obligation
calibration
manufacturing-requirement
diagnostic
failure-mode
use-case
scenario
```

without modifying EKF.

---

# 8. Relationships

Relationships create the engineering knowledge graph.

Relationships are stored in the `relations` field.

Example:

```yaml
relations:

  - type: derives-from
    target: INTENT-SAFE-001

  - type: allocated-to
    target: COMP-CONTACTOR-001

  - type: verified-by
    target: VER-HV-022
```

A relationship MUST contain:

```yaml
type:
target:
```

when referencing another EKF artifact.

---

# 9. Core relationship vocabulary

EKF v0.1 recommends the following relationships:

```text
derives-from
refines
depends-on
allocated-to
implemented-by
verified-by
validated-by
mitigates
interfaces-with
supersedes
produces
```

Their meanings are:

### derives-from

Artifact A originates from artifact B.

```text
A → derives-from → B
```

### refines

Artifact A provides additional detail to B.

### depends-on

A depends on B being true, available or correctly implemented.

### allocated-to

An engineering responsibility is allocated to a component or subsystem.

### implemented-by

A behaviour, design or requirement is implemented by another artifact or engineering resource.

### verified-by

A claim is verified by a verification definition.

### validated-by

An engineering intent or system behaviour is validated by another artifact.

### mitigates

A design element or requirement mitigates a risk or hazard.

### interfaces-with

Two engineering entities interact through an interface.

### supersedes

A replaces an older engineering concept.

### produces

An activity or verification produces another artifact, normally evidence.

---

# 10. Relationships to engineering resources

Not everything referenced by EKF needs to be represented as an EKF artifact.

A relationship MAY reference a repository resource.

Example:

```yaml
relations:

  - type: implemented-by
    resource: src/hv/contactors.c

  - type: implemented-by
    resource: models/hv_contactor.slx
```

A resource MAY represent:

* source code
* CAD
* simulation models
* configuration
* test scripts
* schematics
* generated reports
* data sets

Future EKF versions MAY define URI schemes for external engineering resources.

---

# 11. Artifact content

The Markdown body contains the engineering meaning of the artifact.

EKF deliberately avoids enforcing a rigid body schema.

However, artifacts SHOULD use meaningful Markdown structure.

For example, a requirement might contain:

```text
# Emergency shutdown

## Statement

...

## Acceptance criteria

...

## Rationale

...

## Notes

...
```

A decision might contain:

```text
# Contactor topology

## Context

...

## Decision

...

## Alternatives considered

...

## Consequences

...
```

A verification artifact might contain:

```text
# Emergency shutdown verification

## Objective

...

## Preconditions

...

## Method

...

## Expected result

...

## Pass criteria

...
```

---

# 12. Assumptions are first-class engineering objects

Agents MUST NOT silently convert uncertainty into fact.

Significant uncertainty SHOULD instead be represented explicitly.

Example:

```yaml
---
ekf: "0.1"
id: ASM-HV-003
type: assumption
title: Maximum external shutdown latency
---
```

The body may state:

```text
The external emergency controller is assumed to assert
the shutdown signal within 50 ms.
```

Other artifacts can then use:

```yaml
relations:

  - type: depends-on
    target: ASM-HV-003
```

This allows agents to identify engineering decisions that rely on unresolved assumptions.

---

# 13. Verification and evidence

EKF distinguishes between **verification definition** and **verification evidence**.

A verification artifact describes how something will be verified.

Example:

```text
VER-HV-022
```

An evidence artifact describes the result of performing that verification.

Example:

```text
EVID-HV-022-20260921
```

Relationships might be:

```text
REQ-HV-014
    ↓ verified-by
VER-HV-022
    ↓ produces
EVID-HV-022-20260921
```

Evidence MAY also reference external data:

```yaml
relations:

  - type: produces
    resource: test-results/hv-test-20260921.parquet
```

This distinction allows an agent to determine whether:

* verification has been planned
* verification has been executed
* evidence exists
* evidence applies to the current system baseline

---

# 14. Provenance

EKF artifacts MAY record their origin.

Example:

```yaml
sources:

  - resource: customer-specification.pdf
    title: Customer HV Requirements
```

Machine-generated artifacts SHOULD identify how they were created.

Example:

```yaml
generated:
  by: agent:systems-engineering-agent
  at: 2026-09-21T10:30:00+02:00
```

Human-generated content MAY use:

```yaml
generated:
  by: human:jesper
  at: 2026-09-21T10:30:00+02:00
```

These conventions intentionally align with the provenance philosophy used by OKF.

---

# 15. Verification of engineering knowledge

An artifact MAY record review or verification events.

Example:

```yaml
verified:

  - by: human:system-owner
    at: 2026-09-22T13:00:00+02:00
```

Machine review MAY also be recorded:

```yaml
verified:

  - by: agent:requirement-review-agent
    at: 2026-09-22T12:45:00+02:00
```

Human verification and machine verification are different signals and MUST remain distinguishable.

---

# 16. Lifecycle

Artifacts MAY use:

```yaml
status: draft
```

or:

```yaml
status: stable
```

or:

```yaml
status: deprecated
```

A deprecated artifact SHOULD normally indicate its replacement using:

```yaml
relations:

  - type: supersedes
    target: OLD-REQ-017
```

where appropriate.

Git history remains the authoritative history of previous artifact versions.

---

# 17. Engineering changes

An engineering change SHOULD normally be performed on a Git branch.

Example:

```text
change/16-cell-module
```

The branch contains the complete proposed future state of the engineering system.

An AI agent MAY create or update the branch.

The resulting pull request represents an **engineering change proposal**.

The pull request SHOULD show:

```text
Artifacts added
Artifacts modified
Artifacts removed

Relationships added
Relationships removed

Implementation changes

Verification impact

Potentially affected artifacts

Unresolved assumptions

Agent findings
```

Human reviewers evaluate the engineering change rather than manually maintaining a separate change database.

---

# 18. Baselines

An engineering baseline is identified by a Git commit.

A baseline SHOULD normally be given a Git tag.

Example:

```text
prototype-3
system-v2.3
release-2027.1
```

This means that requirements, architecture, code, verification and engineering evidence can all refer to the same immutable engineering state.

---

# 19. Derived views

The EKF repository is the source.

Views are generated.

Examples include:

```text
Requirements specification
System architecture document
Interface control document
Traceability matrix
Verification matrix
Safety traceability
Change impact report
Compliance report
Design review package
```

These SHOULD normally be generated from EKF rather than independently maintained.

The same engineering graph may therefore produce different views for:

```text
engineer
project manager
customer
safety assessor
regulator
test engineer
AI agent
```

without duplicating the underlying engineering knowledge.

---

# 20. Engineering CI

An EKF repository SHOULD support automated engineering validation.

Deterministic validation SHOULD include at least:

```text
✓ YAML parses correctly
✓ required metadata exists
✓ artifact IDs are unique
✓ referenced artifact IDs exist
```

Projects MAY add rules such as:

```text
✓ every safety requirement has verification

✓ every verification has acceptance criteria

✓ every accepted interface has owners on both sides

✓ every hazard has a mitigation or explicit acceptance

✓ evidence corresponds to the current design baseline
```

Agent-based engineering CI MAY perform semantic checks such as:

```text
⚠ Requirement REQ-HV-014 may conflict with INT-CAN-008

⚠ Verification VER-HV-022 does not appear to test
  the required 250 ms timing

⚠ Architecture document ARCH-HV-003 still describes
  a 15-cell module while the proposed design contains 16 cells

⚠ Requirement REQ-THERM-017 appears unverifiable as written
```

AI-generated semantic findings SHOULD normally be advisory unless project governance explicitly defines otherwise.

---

# 21. Agent behaviour

An engineering agent operating on EKF SHOULD:

1. Preserve artifact IDs.

2. Prefer modifying existing concepts over creating duplicates.

3. Create explicit assumptions when important information is uncertain.

4. Maintain relationships when modifying engineering knowledge.

5. Perform impact analysis before significant changes.

6. Distinguish factual evidence from inference.

7. Record provenance for substantial agent-generated content.

8. Avoid silently modifying stable engineering baselines.

9. Prefer proposing significant engineering changes through Git branches or pull requests.

10. Explain unresolved engineering questions rather than inventing answers.

11. Use deterministic engineering tools when appropriate rather than relying only on language-model reasoning.

12. Create additional tools when necessary to perform an engineering task reliably.

13. Preserve reusable tools when they provide lasting engineering value.

---

# 22. Agent tool environment

An EKF engineering agent SHOULD have access to a controlled execution environment.

A typical environment may provide:

```text
Shell / Bash
Python
Git
compiler toolchains
package managers
test frameworks
simulation tools
repository files
engineering APIs
graph queries
data-processing utilities
```

The environment SHOULD allow the agent to:

```text
inspect
calculate
transform
simulate
compile
execute
test
compare
visualize
validate
generate
```

engineering information.

The execution environment SHOULD preferably be sandboxed and SHOULD use explicit permissions for sensitive external systems or destructive operations.

---

# 23. Dynamic tool creation

An EKF agent SHOULD be able to create temporary or persistent tools when the required capability does not already exist.

For example, given:

```text
test-results/shutdown-run-042.csv
```

the agent may decide that interpreting the result manually is unreliable.

It may create:

```text
tools/analyze_shutdown.py
```

which:

1. reads the measurement data
2. detects shutdown assertion
3. detects when current falls below 1 A
4. calculates elapsed time
5. compares the result with REQ-HV-014
6. produces structured evidence

The agent might execute:

```text
python tools/analyze_shutdown.py \
    test-results/shutdown-run-042.csv
```

and receive:

```text
Shutdown asserted: 10.522 s
Current < 1 A:     10.713 s
Elapsed:           191 ms

REQ-HV-014 limit:  250 ms

RESULT: PASS
Margin: 59 ms
```

The resulting information can then become EKF evidence.

```text
REQ-HV-014
      ↓ verified-by
VER-HV-022
      ↓ executed-using
tools/analyze_shutdown.py
      ↓ produces
EVID-HV-022-RUN042
```

This makes tool creation part of the engineering reasoning loop.

---

# 24. Temporary and persistent tools

Agent-created tools MAY be temporary.

For example:

```text
/tmp/ekf-agent/plot_voltage.py
```

may exist only to answer one engineering question.

Tools that provide reusable engineering capability SHOULD normally be stored in the repository.

Example:

```text
tools/
    check-can-database.py
    analyze-shutdown.py
    compare-calibration.py
    generate-traceability.py
```

Persistent tools SHOULD be version controlled.

This provides:

* reproducibility
* reviewability
* provenance
* reuse
* deterministic reruns

---

# 25. Tool provenance

Engineering conclusions produced using tools SHOULD be reproducible where practical.

Evidence MAY therefore describe the tool and command used.

Example:

```yaml
execution:
  tool: tools/analyze_shutdown.py
  tool_revision: 4c182ab
  command: >
    python tools/analyze_shutdown.py
    test-results/shutdown-run-042.csv
```

For externally provided tools:

```yaml
execution:
  tool: matlab
  version: R2026a
  script: verification/shutdown_analysis.m
```

This allows another engineer or agent to reproduce the engineering result.

---

# 26. Agent-generated tools are engineering artifacts

A tool created by an agent can itself become engineering knowledge.

For important or persistent tools, the repository MAY describe them using EKF.

Example:

```yaml
---
ekf: "0.1"
id: TOOL-HV-004
type: tool
title: Emergency shutdown timing analyzer

relations:
  - type: supports
    target: VER-HV-022
---
```

The implementation may be linked as:

```yaml
relations:

  - type: implemented-by
    resource: tools/analyze_shutdown.py
```

EKF therefore allows engineering methods themselves to become versioned, traceable and reviewable.

---

# 27. Tool safety and control

Access to a generic execution environment introduces capabilities beyond document editing.

An EKF environment SHOULD therefore distinguish between actions such as:

```text
read
write
execute
network-access
external-system-write
hardware-control
destructive-operation
```

Projects MAY require human approval before certain classes of actions.

For example:

```text
read repository                  automatic
run Python analysis              automatic
run simulation                   automatic
create Git branch                automatic
modify draft artifacts           automatic
merge stable baseline            approval required
change external PLM record       approval required
control test hardware            policy dependent
deploy production firmware       approval required
```

EKF does not define a universal permission policy.

The principle is that **agent autonomy should increase where actions are reversible, isolated and verifiable**.

---

# 28. Agent context

An agent SHOULD NOT need the complete repository in its context window.

The EKF graph can be used to construct a relevant engineering context dynamically.

For example:

```text
User:
Why did emergency shutdown test 37 fail?

Agent context:

REQ-HV-014
      ↓
VER-HV-022
      ↓
EVID-HV-022-TEST37

plus:

allocated component
implementation
relevant interfaces
recent decisions
related assumptions
Git change history
```

The agent may additionally use tools to inspect the underlying engineering data.

For example:

```text
Agent
  ↓
reads EKF graph
  ↓
finds relevant test result
  ↓
creates Python analysis tool
  ↓
executes analysis
  ↓
compares result with requirement
  ↓
updates evidence
  ↓
explains conclusion
```

EKF therefore acts as both:

1. the engineering source of truth, and
2. a structured mechanism for constructing agent context and actions.

---

# 29. Graph generation

Tools MAY build a graph index from EKF artifacts.

For example:

```text
REQ-HV-014
   |
   +-- derives-from --> INTENT-SAFE-001
   |
   +-- allocated-to --> COMP-CONTACTOR-001
   |
   +-- verified-by --> VER-HV-022
                           |
                           +-- produces --> EVID-HV-022-20260921
```

Generated graph indexes are caches.

They MUST be reproducible from the EKF source files.

They SHOULD NOT contain engineering information that exists nowhere in the EKF repository.

---

# 30. Conformance

A repository is **EKF v0.1 syntactically conformant** when:

1. Every EKF artifact contains parseable YAML frontmatter.
2. Every EKF artifact contains `ekf`, `id`, `type` and `title`.
3. Every artifact ID is unique.
4. Relationships follow the EKF relationship syntax.

A repository is **EKF v0.1 graph conformant** when, additionally:

1. Every internal relationship target resolves to an EKF artifact.
2. The engineering graph can be constructed without ambiguous artifact identities.

Broken semantic relationships do not make the repository syntactically invalid but SHOULD be reported by engineering CI.

---

# 31. Non-goals

EKF v0.1 does NOT attempt to define:

* a requirements management application
* a systems-engineering process
* a development lifecycle
* a safety lifecycle
* a central taxonomy for all engineering concepts
* an ontology for every engineering discipline
* a database architecture
* a graph database
* a vector database
* an AI model
* a user interface
* a particular agent implementation
* a particular agent runtime
* a particular programming language
* a replacement for domain-specific models such as SysML, CAD, source code or simulation models

EKF connects these engineering resources.

It does not attempt to replace them.

---

# 32. Minimal valid example

The following is a complete EKF artifact:

```yaml
---
ekf: "0.1"
id: REQ-HV-014
type: requirement
title: Emergency shutdown
---

The battery shall disconnect its DC output when the
emergency shutdown input is asserted.
```

Everything beyond this provides additional engineering meaning.

---

# 33. The central EKF idea

Traditional systems-engineering tools primarily manage documents and records.

EKF manages **engineering meaning**.

```text
              Intent
                │
                ▼
           Requirements
                │
         ┌──────┴──────┐
         ▼             ▼
      Design        Interfaces
         │             │
         └──────┬──────┘
                ▼
          Implementation
                │
                ▼
          Verification
                │
                ▼
             Evidence
```

The graph is stored as simple files.

Git stores its evolution.

Agents maintain and analyze it.

Agents can use existing engineering tools and create new tools when necessary.

A controlled execution environment lets the agent move beyond language reasoning and perform deterministic calculations, simulations, transformations and analyses.

Humans provide intent, engineering judgement and approval.

Views such as requirements specifications, traceability matrices and verification reports are generated from the graph rather than becoming independent sources of truth.

**EKF therefore treats systems engineering as a continuously evolving, version-controlled, executable engineering knowledge system rather than a collection of documents in a requirements database.**
