# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class ProbeRecord:
    label: str
    count: u8


class Contract(gl.Contract):
    records: TreeMap[str, ProbeRecord]
    owner: Address
    state: str

    def __init__(self):
        self.owner = gl.message.sender_address
        self.state = "READY"

    @gl.public.write
    def seed(self, key: str, label: str, count: u8) -> None:
        self.records[key] = ProbeRecord(label, count)

    @gl.public.write
    def probe_web(self, url: str) -> None:
        target = str(url)

        def leader_fn():
            response = gl.nondet.web.get(target)
            return response.status == 200

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            response = gl.nondet.web.get(target)
            return leader_result.calldata == (response.status == 200)

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.state = "AVAILABLE" if result else "UNAVAILABLE"

    @gl.public.view
    def get_state(self) -> str:
        return self.state
