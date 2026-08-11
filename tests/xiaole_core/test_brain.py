import unittest

from xiaole_core.brain import BrainCore
from xiaole_core.errors import MemoryUnavailable
from xiaole_core.gateways.action import ActionGateway
from xiaole_core.schemas import ActionResult, BrainRequest, MemoryResult


class Context:
    def __init__(self): self.exchanges=[]
    def resolve(self, user, cid, _message): return cid or "new-cid"
    def history(self, _user, _cid): return []
    def append_exchange(self, user, cid, message, answer): self.exchanges.append((user,cid,message,answer))


class Model:
    def __init__(self): self.calls=0
    def complete(self, *_):
        self.calls += 1
        return type("Result", (), {"text":"普通回答","model":"deepseek","fallback":False})()


class Gateway:
    def __init__(self, result=None, error=None): self.result,self.error,self.calls=result,error,0
    def ask(self, *_):
        self.calls += 1
        if self.error: raise self.error
        return self.result
    def execute(self, *_): self.calls += 1; return self.result


class BrainTests(unittest.TestCase):
    def test_conversation_calls_no_gateway(self):
        memory, action = Gateway(), Gateway()
        response = BrainCore(Context(), Model(), memory, action).respond(BrainRequest(message="你好"), "alice")
        self.assertEqual(response.intent.value, "conversation")
        self.assertEqual((memory.calls, action.calls), (0,0))

    def test_memory_is_grounded_and_preserves_sources_without_second_generation(self):
        sources=[{"title":"原始通知","custom":"complete"}]
        memory=Gateway(MemoryResult(answer="乐知事实",sources=sources,confidence="grounded",request_id="ignored"))
        model=Model()
        response=BrainCore(Context(),model,memory,Gateway()).respond(BrainRequest(message="最近有什么官方通知？"),"alice")
        self.assertEqual(response.answer,"乐知事实")
        self.assertEqual(response.sources,sources)
        self.assertEqual(model.calls,0)

    def test_memory_unavailable_is_honest(self):
        response=BrainCore(Context(),Model(),Gateway(error=MemoryUnavailable("down")),Gateway()).respond(BrainRequest(message="最近有什么官方通知？"),"alice")
        self.assertEqual(response.sources,[])
        self.assertIn("知识系统暂时不可用",response.answer)

    def test_action_reports_only_gateway_result(self):
        result=ActionResult(task_id="t",status="dead",summary="任务失败",request_id="r")
        action=Gateway(result)
        response=BrainCore(Context(),Model(),Gateway(),action).respond(BrainRequest(message="给我手机发一条测试通知"),"alice")
        self.assertEqual(response.action.status,"dead")
        self.assertNotIn("成功",response.answer)

    def test_unconfigured_action_returns_unavailable_without_legacy_or_network_fallback(self):
        class NoNetworkTransport:
            def post(self, *_args, **_kwargs):
                raise AssertionError("unconfigured Action must not make a network call")

        model, memory = Model(), Gateway()
        response = BrainCore(Context(), model, memory, ActionGateway("", "", transport=NoNetworkTransport())).respond(
            BrainRequest(message="给我手机发一条测试通知"), "alice"
        )
        self.assertIsNone(response.action)
        self.assertIn("执行系统暂时不可用", response.answer)
        self.assertEqual((model.calls, memory.calls), (0, 0))


if __name__ == "__main__": unittest.main()
