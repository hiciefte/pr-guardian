# Tasks: PR Guardian - Autonomous Translation Review Agent

**Input**: Design documents from `/specs/001-pr-guardian-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included as specified in plan.md

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Docker environment

- [ ] T001 Create project directory structure per plan.md (src/models/, src/services/, src/cli/, src/lib/, tests/, docker/, config/)
- [ ] T002 Initialize Python 3.11+ project with pyproject.toml and dependencies (anthropic, pydantic, tenacity, gitpython, pyyaml, click, redis)
- [ ] T003 [P] Configure ruff for linting and black for formatting
- [ ] T004 [P] Create .gitignore with secrets/, __pycache__/, .env patterns
- [ ] T005 [P] Create requirements.txt from plan.md dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

### Configuration & Models

- [ ] T006 Create PRGuardianConfiguration model in src/models/config.py with validation rules
- [ ] T007 [P] Create RepositoryTarget model in src/models/repository.py with translation patterns
- [ ] T008 [P] Create TranslationPullRequest model in src/models/pull_request.py with state transitions
- [ ] T009 [P] Create ReviewComment model in src/models/comment.py
- [ ] T010 [P] Create TranslationExtraction model in src/models/extraction.py with confidence thresholds
- [ ] T011 [P] Create CommentClassification model in src/models/classification.py with priority mapping
- [ ] T012 [P] Create TranslationChange model in src/models/translation.py with placeholder validation
- [ ] T013 [P] Create CommitRecord model in src/models/commit.py with 7-rule validation
- [ ] T014 [P] Create SessionReport model in src/models/session.py
- [ ] T015 [P] Create FeedbackPattern model in src/models/feedback_pattern.py
- [ ] T016 [P] Create FeedbackIssue model in src/models/feedback_issue.py

### Core Infrastructure Services

- [ ] T017 Implement config_loader service in src/services/config_loader.py with YAML parsing and validation
- [ ] T018 [P] Create structured logging utility in src/lib/utils/logging.py with UTC timestamps
- [ ] T019 [P] Create retry utility in src/lib/utils/retry.py with exponential backoff and jitter
- [ ] T020 [P] Create timing utility in src/lib/utils/timing.py with UTC enforcement
- [ ] T021 Implement GitHub CLI client wrapper in src/services/github_client.py with rate limit handling

### Translation File Parsers

- [ ] T022 [P] Create properties parser in src/lib/parsers/properties.py using javaproperties
- [ ] T023 [P] Create JSON parser in src/lib/parsers/json_parser.py with jsonschema validation
- [ ] T024 [P] Create YAML parser in src/lib/parsers/yaml_parser.py with safe_load
- [ ] T025 Create placeholder validator in src/lib/validators/placeholder.py with regex patterns
- [ ] T026 Create syntax validator in src/lib/validators/syntax.py with unified interface

### Docker Configuration

- [ ] T027 Create Dockerfile in docker/Dockerfile with Python 3.11-alpine base
- [ ] T028 [P] Create entrypoint.sh in docker/entrypoint.sh with SSH/GPG setup
- [ ] T029 [P] Create docker-compose.yml in docker/docker-compose.yml with Ofelia and Redis
- [ ] T030 [P] Create config.example.yml in config/config.example.yml
- [ ] T031 [P] Create .env.example in config/.env.example with GH_TOKEN and ANTHROPIC_API_KEY placeholders

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Automated Daily Review Implementation (Priority: P1)

**Goal**: Agent automatically checks for translation PRs, implements CodeRabbitAI comments, and pushes signed commits

**Independent Test**: Configure agent for single repository, create test PR with CodeRabbitAI comments, run agent, verify signed commits pushed

### Tests for User Story 1

- [ ] T032 [P] [US1] Contract test for GitHub PR list API in tests/contract/test_github_api.py
- [ ] T033 [P] [US1] Contract test for GitHub comment retrieval in tests/contract/test_github_api.py
- [ ] T034 [P] [US1] Unit test for comment classification in tests/unit/services/test_comment_classifier.py
- [ ] T035 [P] [US1] Unit test for LLM parser extraction in tests/unit/services/test_llm_parser.py
- [ ] T036 [P] [US1] Unit test for commit message builder in tests/unit/services/test_commit_builder.py
- [ ] T037 [P] [US1] Integration test for PR processing workflow in tests/integration/test_pr_workflow.py

### Implementation for User Story 1

#### PR Discovery & Comment Retrieval

- [ ] T038 [US1] Implement pr_discovery service in src/services/pr_discovery.py with author filtering
- [ ] T039 [US1] Implement comment_retrieval service in src/services/comment_retrieval.py for CodeRabbitAI comments

#### LLM-Based Comment Parsing

- [ ] T040 [US1] Implement llm_parser service in src/services/llm_parser.py with Anthropic Claude 3 Haiku integration
- [ ] T041 [US1] Add parallel comment parsing with asyncio semaphore (10 concurrent) in src/services/llm_parser.py
- [ ] T042 [US1] Implement confidence-based decision logic (0.80/0.60 thresholds) in src/services/llm_parser.py
- [ ] T043 [US1] Add circuit breaker pattern for LLM failure protection in src/services/llm_parser.py

#### Comment Classification

- [ ] T044 [US1] Implement comment_classifier service in src/services/comment_classifier.py with constitution framework
- [ ] T045 [US1] Add priority assignment (Critical=1, Constructive=2, Nitpick=3) in src/services/comment_classifier.py
- [ ] T046 [US1] Add glossary conflict detection for nitpick skip decisions in src/services/comment_classifier.py

#### File Validation & Translation Processing

- [ ] T047 [US1] Implement file_validator service in src/services/file_validator.py with pattern matching
- [ ] T048 [US1] Implement translation_processor service in src/services/translation_processor.py for applying changes
- [ ] T049 [US1] Add placeholder integrity validation before/after changes in src/services/translation_processor.py

#### Commit Creation & Signing

- [ ] T050 [US1] Implement commit_builder service in src/services/commit_builder.py with 7 conventional rules
- [ ] T051 [US1] Add imperative mood conversion helper in src/services/commit_builder.py
- [ ] T052 [US1] Implement gpg_signer service in src/services/gpg_signer.py with web-flow and traditional GPG support
- [ ] T053 [US1] Implement git_operations service in src/services/git_operations.py for commit/push operations
- [ ] T054 [US1] Add rollback capability with git reset --hard in src/services/git_operations.py

#### CLI Interface

- [ ] T055 [US1] Create CLI entry point in src/cli/main.py with Click
- [ ] T056 [US1] Implement run command in src/cli/run.py with timeout handling
- [ ] T057 [US1] Implement config command in src/cli/config.py for validation

**Checkpoint**: User Story 1 complete - agent can process single repository PRs

---

## Phase 4: User Story 4 - Scheduled Execution Management (Priority: P1)

**Goal**: Agent runs reliably on configured schedule with error handling and logging

**Independent Test**: Configure schedule, simulate failures (rate limits, network errors), verify graceful handling and recovery

### Tests for User Story 4

- [ ] T058 [P] [US4] Unit test for timeout handling in tests/unit/services/test_session_manager.py
- [ ] T059 [P] [US4] Unit test for error recovery logic in tests/unit/services/test_session_manager.py
- [ ] T060 [P] [US4] Integration test for scheduled execution in tests/integration/test_scheduled_execution.py

### Implementation for User Story 4

- [ ] T061 [US4] Implement session_manager service in src/services/session_manager.py with orchestration logic
- [ ] T062 [US4] Add execution timeout with SIGALRM handling (30min default) in src/services/session_manager.py
- [ ] T063 [US4] Add healthchecks.io integration for monitoring in src/services/session_manager.py
- [ ] T064 [US4] Implement comprehensive logging for session start/end/errors in src/services/session_manager.py
- [ ] T065 [US4] Add rate limit handling with exponential backoff retry in src/services/github_client.py
- [ ] T066 [US4] Implement GPG signing failure rollback logic in src/services/git_operations.py

**Checkpoint**: User Stories 1 and 4 complete - core autonomous workflow functional

---

## Phase 5: User Story 2 - Multi-Repository Monitoring (Priority: P2)

**Goal**: Agent monitors PRs across multiple GitHub repositories in single execution

**Independent Test**: Configure 3 repositories, create PRs in 2, verify agent processes all independently

### Tests for User Story 2

- [ ] T067 [P] [US2] Unit test for multi-repository processing in tests/unit/services/test_session_manager.py
- [ ] T068 [P] [US2] Integration test for multi-repository workflow in tests/integration/test_multi_repo.py

### Implementation for User Story 2

- [ ] T069 [US2] Add repository iteration in session_manager with independent contexts in src/services/session_manager.py
- [ ] T070 [US2] Implement fair workload allocation across repositories in src/services/session_manager.py
- [ ] T071 [US2] Add per-repository error isolation (continue on partial failures) in src/services/session_manager.py
- [ ] T072 [US2] Update session report aggregation for multiple repositories in src/models/session.py

**Checkpoint**: User Stories 1, 2, and 4 complete - multi-repository support

---

## Phase 6: User Story 3 - Feedback Loop via Issue Creation (Priority: P3)

**Goal**: Agent creates issues summarizing CodeRabbitAI feedback patterns for translation system improvements

**Independent Test**: Run agent with issue creation enabled, verify formatted issues with statistics and recommendations

### Tests for User Story 3

- [ ] T073 [P] [US3] Unit test for feedback aggregation in tests/unit/services/test_feedback_aggregator.py
- [ ] T074 [P] [US3] Unit test for issue creation in tests/unit/services/test_issue_creator.py
- [ ] T075 [P] [US3] Integration test for feedback loop in tests/integration/test_feedback_loop.py

### Implementation for User Story 3

- [ ] T076 [US3] Implement feedback_aggregator service in src/services/feedback_aggregator.py with pattern detection
- [ ] T077 [US3] Add terminology, punctuation, formality pattern recognition in src/services/feedback_aggregator.py
- [ ] T078 [US3] Add severity classification (critical/moderate/minor) for patterns in src/services/feedback_aggregator.py
- [ ] T079 [US3] Implement issue_creator service in src/services/issue_creator.py with GitHub issue API
- [ ] T080 [US3] Create issue body template with markdown formatting in src/services/issue_creator.py
- [ ] T081 [US3] Add skip logic when no actionable patterns detected in src/services/issue_creator.py
- [ ] T082 [US3] Implement PR summary comment posting with implementation status table in src/services/github_client.py

**Checkpoint**: All user stories complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, optimization, and production hardening

### Documentation

- [ ] T083 [P] Create README.md with setup and usage instructions
- [ ] T084 [P] Update quickstart.md with any implementation changes

### Testing & Validation

- [ ] T085 [P] Add unit tests for all models in tests/unit/models/
- [ ] T086 [P] Add unit tests for parsers in tests/unit/lib/parsers/
- [ ] T087 Run full test suite with coverage report
- [ ] T088 Execute quickstart.md validation end-to-end

### Production Hardening

- [ ] T089 [P] Add semantic caching with Redis in src/services/llm_parser.py
- [ ] T090 [P] Implement validate command for pre-execution checks in src/cli/validate.py
- [ ] T091 Code cleanup and refactoring across all services
- [ ] T092 Security audit for secrets handling and token redaction

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 and US4 (both P1) can proceed in parallel after Foundation
  - US2 (P2) can start after US1 core services exist
  - US3 (P3) can start after US1 core services exist
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 4 (P1)**: Can start after Foundational (Phase 2) - shares github_client with US1
- **User Story 2 (P2)**: Depends on session_manager from US4
- **User Story 3 (P3)**: Depends on core services from US1

### Within Each User Story

- Tests written first, must FAIL before implementation
- Models before services
- Services before CLI
- Core implementation before integration

### Parallel Opportunities

**Phase 2 (Foundational)**:
```bash
# All models can run in parallel:
T007, T008, T009, T010, T011, T012, T013, T014, T015, T016

# All parsers can run in parallel:
T022, T023, T024

# All Docker config can run in parallel:
T028, T029, T030, T031
```

**Phase 3 (User Story 1)**:
```bash
# All tests can run in parallel:
T032, T033, T034, T035, T036, T037
```

**Cross-Story Parallelism**:
- After Foundation complete, US1 and US4 can start in parallel
- After US1/US4 core complete, US2 and US3 can start in parallel

---

## Implementation Strategy

### MVP First (User Stories 1 + 4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (core PR processing)
4. Complete Phase 4: User Story 4 (reliable scheduling)
5. **STOP and VALIDATE**: Test autonomous workflow end-to-end
6. Deploy for production use

### Incremental Delivery

1. Setup + Foundational + US1 + US4 = MVP (autonomous PR processing)
2. Add US2 = Multi-repository support
3. Add US3 = Feedback loop for continuous improvement
4. Each story adds value without breaking previous stories

### Cost Optimization Path

- Start without Redis (direct LLM calls): ~$2.40/month
- Add Redis semantic caching (T089): ~$1.13/month
- Monitor usage at https://console.anthropic.com/settings/usage

---

## Task Summary

- **Total Tasks**: 92
- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 26 tasks
- **Phase 3 (US1)**: 26 tasks
- **Phase 4 (US4)**: 9 tasks
- **Phase 5 (US2)**: 6 tasks
- **Phase 6 (US3)**: 10 tasks
- **Phase 7 (Polish)**: 10 tasks

**MVP Scope**: Phases 1-4 (66 tasks) delivers complete autonomous PR processing

**Parallel Opportunities**: 47 tasks marked [P] can run concurrently with appropriate grouping

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- LLM costs: $1.13-2.40/month for 6,000 requests
