import json

import cloudpickle
import pytest


URL_A = "https://agency.example/notices/alpha"
URL_B = "https://archive.example/notices/alpha"


def body(
    notice_id="PN-42",
    revision="2026.08",
    effective_date="2026-08-01",
    retrieved_at="2026-08-15",
    content="same text",
):
    return json.dumps(
        {
            "notice_id": notice_id,
            "revision": revision,
            "effective_date": effective_date,
            "retrieved_at": retrieved_at,
            "content": content,
        }
    )


def create(contract, direct_vm, direct_owner):
    direct_vm.sender = direct_owner
    contract.create_case(
        "case-42",
        "public-notice-42",
        URL_A,
        URL_B,
        "PN-42",
        "PN-42",
        "2026.08",
        "2026.08",
        "2026-08-01",
        "2026-08-01",
        "2026-08-01",
        "2026-08-31",
    )


def mock_sources(direct_vm, content_a="same text", content_b="same text", **kwargs):
    direct_vm.mock_web(r"agency\.example", {"method": "GET", "status": 200, "body": body(content=content_a, **kwargs)})
    direct_vm.mock_web(r"archive\.example", {"method": "GET", "status": 200, "body": body(content=content_b, **kwargs)})


def mock_header_sources(direct_vm):
    response = {
        "status": 200,
        "headers": {"Date": "Sat, 15 Aug 2026 00:00:00 GMT"},
        "body": body(retrieved_at=""),
    }
    direct_vm.mock_web(r"agency\.example", {"method": "GET", "response": response})
    direct_vm.mock_web(r"archive\.example", {"method": "GET", "response": response})


def test_lifecycle_and_consistent_result(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    assert json.loads(contract.get_result("case-42"))["state"] == "DRAFT"

    contract.freeze_case("case-42")
    mock_sources(direct_vm)
    contract.assess("case-42")

    result = json.loads(contract.get_result("case-42"))
    assert result["state"] == "ASSESSED"
    assert result["outcome"] == "CONSISTENT"
    assert result["digest_a"] == result["digest_b"]


def test_conflicting_sources_are_recorded(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_sources(direct_vm, content_b="changed text")
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "CONFLICTING"


def test_missing_version_is_fail_closed(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_sources(direct_vm, revision="")
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "MISSING_VERSION"


def test_unavailable_source_is_unresolved_and_retry_is_bounded(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    direct_vm.mock_web(r"agency\.example", {"method": "GET", "status": 429, "body": ""})
    direct_vm.mock_web(r"archive\.example", {"method": "GET", "status": 200, "body": body()})
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "UNRESOLVED"

    for _ in range(2):
        direct_vm.clear_mocks()
        direct_vm.mock_web(r"agency\.example", {"method": "GET", "status": 429, "body": ""})
        direct_vm.mock_web(r"archive\.example", {"method": "GET", "status": 200, "body": body()})
        contract.retry_unresolved("case-42")
    with direct_vm.expect_revert("retry limit"):
        contract.retry_unresolved("case-42")
    assert json.loads(contract.get_result("case-42"))["retry_count"] == 2


def test_provenance_mismatch_is_unresolved(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_sources(direct_vm, revision="2026.09")
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "UNRESOLVED"


def test_malformed_source_is_unresolved(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    direct_vm.mock_web(r"agency\.example", {"method": "GET", "status": 200, "body": "not-json"})
    direct_vm.mock_web(r"archive\.example", {"method": "GET", "status": 200, "body": body()})
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "UNRESOLVED"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"retrieved_at": "2026-08-01"},
        {"retrieved_at": "2026-08-31"},
        {"retrieved_at": "2026-07-31"},
        {"retrieved_at": "2026-09-01"},
    ],
)
def test_retrieval_window_is_enforced_inclusive(direct_vm, direct_deploy, direct_owner, kwargs):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_sources(direct_vm, **kwargs)
    contract.assess("case-42")
    expected = "CONSISTENT" if kwargs["retrieved_at"] in {"2026-08-01", "2026-08-31"} else "UNRESOLVED"
    assert json.loads(contract.get_result("case-42"))["outcome"] == expected


def test_http_retrieval_date_header_is_supported(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_header_sources(direct_vm)
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "CONSISTENT"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"notice_id": 42},
        {"notice_id": "x" * 257},
        {"effective_date": "2026-99-99"},
        {"retrieved_at": "not-a-date"},
    ],
)
def test_fetched_metadata_must_be_strict_and_bounded(direct_vm, direct_deploy, direct_owner, kwargs):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_sources(direct_vm, **kwargs)
    contract.assess("case-42")
    assert json.loads(contract.get_result("case-42"))["outcome"] == "UNRESOLVED"


def test_validator_rejects_changed_decision(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    contract.freeze_case("case-42")
    mock_sources(direct_vm)
    contract.assess("case-42")
    _, leader_fn, validator_fn = direct_vm._captured_validators[-1]
    cloudpickle.loads(cloudpickle.dumps(leader_fn))
    cloudpickle.loads(cloudpickle.dumps(validator_fn))
    direct_vm.clear_mocks()
    mock_sources(direct_vm, content_b="changed text")
    assert direct_vm.run_validator() is False


def test_owner_and_state_transitions_are_enforced(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    with direct_vm.prank("0x" + "1" * 40):
        with direct_vm.expect_revert("only the owner"):
            contract.freeze_case("case-42")
    contract.freeze_case("case-42")
    with direct_vm.expect_revert("case is not draft"):
        contract.freeze_case("case-42")
    mock_sources(direct_vm)
    contract.assess("case-42")
    with direct_vm.expect_revert("case is not assessable"):
        contract.assess("case-42")


def test_duplicate_case_and_invalid_dates_are_rejected(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/notice_registry.py")
    create(contract, direct_vm, direct_owner)
    with direct_vm.expect_revert("case already exists"):
        create(contract, direct_vm, direct_owner)


@pytest.mark.parametrize(
    "method,args",
    [
        ("create_case", ("bad", "subject", "http://a", URL_B, "id", "id", "r", "r", "2026-01-01", "2026-01-01", "2026-01-01", "2026-01-02")),
        ("create_case", ("bad", "subject", URL_A, URL_A, "id", "id", "r", "r", "2026-01-01", "2026-01-01", "2026-01-01", "2026-01-02")),
        ("create_case", ("bad", "subject", URL_A, URL_B, "id", "id", "r", "r", "2026-02-30", "2026-01-01", "2026-01-01", "2026-01-02")),
        ("create_case", ("bad", "subject", URL_A, URL_B, "id", "id", "r", "r", "2026-01-01", "2026-01-01", "2026-02-01", "2026-01-01")),
        ("create_case", ("bad", "x" * 257, URL_A, URL_B, "id", "id", "r", "r", "2026-01-01", "2026-01-01", "2026-01-01", "2026-01-02")),
    ],
)
def test_create_rejects_invalid_sources(direct_vm, direct_deploy, direct_owner, method, args):
    contract = direct_deploy("contracts/notice_registry.py")
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert():
        getattr(contract, method)(*args)
