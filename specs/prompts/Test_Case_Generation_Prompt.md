# Generate Manual QA Test Cases

## Objective

Generate a complete manual testing suite for the EchoWell application.

The test cases will be used by:

- QA Testers
- Developers
- Product Owners
- Research Team Members

The testing suite must verify all functionality implemented in the application.

---

## Source Documents

Read:

```text
specs/TRDS/
specs/backlog/BACKLOG.md
specs/backlog/features/
docs/design/
specs/UI-wireframe/
```

Treat these documents as the source of truth.

---

## Output Location

Create:

```text
specs/testing/test-cases/
```

Generate:

```text
TC-001-<Feature-Name>.md
TC-002-<Feature-Name>.md
TC-003-<Feature-Name>.md
...
```

Create one file for every feature defined in:

```text
specs/backlog/features/
```

---

## Coverage Requirements

The generated test suite must cover:

### Positive Testing

Verify:

- Expected user behavior
- Expected workflows
- Expected calculations
- Expected database updates
- Expected API interactions

---

### Negative Testing

Verify:

- Invalid inputs
- Missing inputs
- Invalid API requests
- Database failures
- Missing records
- Error handling
- Network failures
- Unauthorized access attempts

---

### UI Testing

Verify:

- Navigation
- Screens
- Components
- Sorting
- Filtering
- Forms
- Tables
- Visual indicators
- Status messages
- Error messages

---

### API Testing

Verify:

- Endpoint behavior
- Required parameters
- Validation rules
- Error responses
- Data integrity

---

### Database Testing

Verify:

- Records created
- Records updated
- Records deleted when applicable
- Foreign key relationships
- Data integrity

---

### Analytics Testing

Verify:

- Baseline creation
- Baseline freeze behavior
- Duplicate handling
- Quality screening
- Morning adjustments
- Epoch resets
- Composite scoring
- CUSUM calculations
- Alert generation

---

## Test Case File Structure

Each file shall contain:

# Feature Name

## Feature Description

Brief feature summary.

## Preconditions

List all required setup conditions.

---

## Manual Test Cases

Use the following table format.

| Test Case ID | Test Scenario | Priority | Type |
|--------------|---------------|----------|------|
| TC-001 | Example Scenario | High | Positive |

---

### Test Steps

| Step | Action | Expected Result |
|--------|---------|----------------|
| 1 | Navigate to Residents page | Residents page opens |
| 2 | Click Sort by Alarm | Residents sorted correctly |
| 3 | Verify resident order | Correct order displayed |

---

## API Validation

Include:

| Step | API Action | Expected Result |
|--------|------------|----------------|
| 1 | GET /residents | 200 OK |
| 2 | Verify response schema | Matches OpenAPI specification |

---

## Database Validation

Include:

| Step | Database Check | Expected Result |
|--------|----------------|----------------|
| 1 | Query residents table | Correct row exists |
| 2 | Verify status field | Matches UI value |

---

## Negative Test Cases

Include:

| Step | Action | Expected Result |
|--------|---------|----------------|
| 1 | Submit invalid input | Validation error displayed |
| 2 | Remove required field | Request rejected |
| 3 | Simulate API failure | User sees error message |

---

## Acceptance Criteria Validation

For each acceptance criterion:

| Requirement | Pass Condition |
|-------------|---------------|
| AC-001 | Requirement satisfied |
| AC-002 | Requirement satisfied |

---

## Test Data Requirements

List:

- Required data
- Mock records
- Required environment variables
- Required resident records

---

## Traceability

Map:

| Requirement | Feature | Test Case |
|-------------|---------|-----------|
| TRD-001 | FEAT-001 | TC-001 |
| TRD-002 | FEAT-001 | TC-002 |

---

## Additional Requirements

1. Every feature must have positive tests.
2. Every feature must have negative tests.
3. Every feature must include UI validation where applicable.
4. Every feature must include API validation where applicable.
5. Every feature must include database validation where applicable.
6. Every acceptance criterion must be tested.
7. Every test case must be executable by a QA tester without additional knowledge.
8. Expected results must be specific and measurable.
9. No vague expected results such as:
   - "Works correctly"
   - "Looks good"
   - "Functions properly"

Instead use precise outcomes.

Example:

✅ Good:

```text
Alarm badge displays "Alarm On" in red.
```

❌ Bad:

```text
Alarm status appears correctly.
```

10. All test cases must be implementation-ready and suitable for manual validation before production deployment.