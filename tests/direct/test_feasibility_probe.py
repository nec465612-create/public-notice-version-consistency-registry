import cloudpickle


def test_probe_web_and_storage(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/feasibility_probe.py")
    direct_vm.sender = direct_owner
    contract.seed("alpha", "sample", 2)
    direct_vm.mock_web(r"example\.org", {"method": "GET", "status": 200, "body": "ok"})
    contract.probe_web("https://example.org")
    assert contract.get_state() == "AVAILABLE"


def test_probe_closures_are_serializable():
    def leader_fn():
        return "READY"

    def validator_fn(leader_result):
        return leader_result.calldata == "READY"

    cloudpickle.loads(cloudpickle.dumps(leader_fn))
    cloudpickle.loads(cloudpickle.dumps(validator_fn))
