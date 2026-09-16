"""Retrieval relevance, evidence boundaries and mixed tool flows. / 检索与引用边界测试。"""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_agent
from agent.agent import CapacityAgent
from agent.demo import parameters
from agent.knowledge import ROOT, search_knowledge
from agent.llm_client import ModelReply, ToolCall
from agent.presentation import format_turn


def reply(
    kind="knowledge",
    english="The retrieved sources explain the project assumptions.",
    chinese="检索资料说明了项目假设。",
):
    return ModelReply(
        text=json.dumps(
            {"kind": kind, "english": english, "chinese": chinese}, ensure_ascii=False
        )
    )


def lookup(query="PUE", call_id="k1"):
    return ModelReply(
        calls=[
            ToolCall(
                call_id, "search_knowledge", json.dumps({"query": query, "top_k": 2})
            )
        ]
    )


class Client:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.histories = []

    def complete(self, history, instructions, tools):
        self.histories.append(history)
        return next(self.replies)


class KnowledgeTests(unittest.TestCase):
    def test_api_key_query_rejected_without_echo(self):
        fake = "sk-" + "TESTONLY" * 5
        with self.assertRaises(ValueError) as context:
            search_knowledge(fake)
        self.assertNotIn(fake, str(context.exception))

    def test_old_turn_evidence_does_not_authorize_new_answer(self):
        client = Client([lookup(), reply(), reply(), lookup("reserve", "k2"), reply()])
        agent = CapacityAgent(client)
        self.assertEqual(agent.ask("Explain PUE").status, "knowledge")
        result = agent.ask("Explain remaining reserve")
        self.assertEqual(result.status, "knowledge")
        self.assertEqual(result.records[0]["query"], "reserve")
        agent.reset()
        self.assertEqual(agent.history, [])

    def test_source_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "knowledge").mkdir(parents=True)
            (Path(tmp) / "outside.md").write_text("outside", encoding="utf-8")
            catalog = json.loads(
                (ROOT / "knowledge/catalog.json").read_text(encoding="utf-8")
            )
            for chunk in catalog:
                chunk["source_file"] = "../outside.md"
            (root / "knowledge/catalog.json").write_text(
                json.dumps(catalog), encoding="utf-8"
            )
            with patch("agent.knowledge.ROOT", root), self.assertRaises(ValueError):
                search_knowledge("PUE")

    def test_prompt_treats_retrieval_as_data(self):
        agent = CapacityAgent(Client([]))
        self.assertIn("untrusted reference data", agent.instructions)
        self.assertIn("use BOTH search_knowledge", agent.instructions)

    def test_bilingual_relevance(self):
        for query, expected in [
            ("What is PUE?", "pue"),
            ("电能使用效率是什么意思", "pue"),
            ("DGX B200 specifications", "hardware"),
            ("剩余功率是安全预留吗", "reserve"),
            ("baseline assumptions", "assumptions"),
            ("断路器变压器选型", "scope"),
            ("rack pod", "layout"),
        ]:
            with self.subTest(query=query):
                self.assertEqual(search_knowledge(query, 1)["hits"][0]["id"], expected)

    def test_no_match_and_path_query(self):
        for query in ["zqxjv", "../../.env", "火星种植土豆"]:
            self.assertEqual(search_knowledge(query)["status"], "no_match")

    def test_parameters_are_validated(self):
        for query, k in [
            ("", 3),
            (" " * 5, 3),
            ("x" * 501, 3),
            (None, 3),
            ("PUE", True),
            ("PUE", 0),
            ("PUE", 6),
            ("PUE", 2.5),
        ]:
            with self.subTest(query=query, k=k), self.assertRaises(ValueError):
                search_knowledge(query, k)

    def test_sources_exist_and_are_stable(self):
        result = search_knowledge("PUE specification rack reserve scope", 5)
        self.assertEqual(
            result, search_knowledge("PUE specification rack reserve scope", 5)
        )
        self.assertEqual(len(result["hits"]), 5)
        for hit in result["hits"]:
            self.assertTrue((ROOT / hit["source_file"]).is_file())
            self.assertTrue(hit["text_en"] and hit["text_zh"] and hit["source_section"])

    def test_knowledge_answer_requires_current_evidence(self):
        agent = CapacityAgent(Client([reply(), lookup(), reply()]))
        result = agent.ask("Explain PUE")
        self.assertEqual(result.status, "knowledge")
        self.assertEqual(len(result.records), 1)
        self.assertIn("README.md", format_turn(result))
        self.assertIn("PUE", format_turn(result))
        self.assertEqual(agent.results, {})
        self.assertFalse(agent.baseline_enabled)

    def test_no_match_cannot_become_knowledge_answer(self):
        agent = CapacityAgent(Client([lookup("zqxjv"), reply(), reply("unsupported")]))
        self.assertEqual(agent.ask("zqxjv").status, "unsupported")

    def test_retrieval_cannot_replace_calculation(self):
        agent = CapacityAgent(Client([lookup(), reply("answer")]), max_rounds=2)
        self.assertEqual(agent.ask("Calculate baseline capacity").status, "limited")

    def test_mixed_flow_keeps_baseline(self):
        calc = ModelReply(
            calls=[
                ToolCall(
                    "c1",
                    "calculate_capacity",
                    json.dumps(
                        {
                            "parameters": parameters(facility_capacity_mw=500),
                            "use_baseline_defaults": True,
                        }
                    ),
                )
            ]
        )
        client = Client([lookup(), calc, reply("answer")])
        turn = CapacityAgent(client).ask(
            "Explain PUE and calculate baseline for 500 MW"
        )
        self.assertEqual(turn.status, "answer")
        self.assertEqual(turn.records[1]["result"]["total_gpus"], 226304)
        self.assertIn("Sources", json.dumps(client.histories))

    def test_invented_citations_are_rejected(self):
        for bad in ["See https://fake.example.", "See [fake].", "See fake.md."]:
            agent = CapacityAgent(Client([lookup(), reply(english=bad), reply()]))
            turn = agent.ask("Explain PUE")
            self.assertNotIn(bad, format_turn(turn))
            self.assertEqual(turn.status, "knowledge")

    def test_unknown_fields_and_plot_source_rejected(self):
        agent = CapacityAgent(Client([]))
        result = agent._invoke(
            "search_knowledge", json.dumps({"query": "PUE", "top_k": 3, "path": ".env"})
        )
        self.assertFalse(result["ok"])
        agent._invoke("search_knowledge", json.dumps({"query": "PUE", "top_k": 3}))
        self.assertFalse(
            agent._invoke(
                "generate_capacity_plot",
                json.dumps({"result_id": "pue", "analysis_type": "capacity"}),
            )["ok"]
        )

    def test_secret_query_and_contaminated_source_rejected(self):
        agent = CapacityAgent(Client([]), secrets=("SECRET_TEST_VALUE",))
        self.assertEqual(agent.ask("SECRET_TEST_VALUE").status, "error")
        with patch(
            "agent.agent.search_knowledge", return_value={"text": "SECRET_TEST_VALUE"}
        ):
            self.assertFalse(
                agent._invoke(
                    "search_knowledge", json.dumps({"query": "PUE", "top_k": 3})
                )["ok"]
            )

    def test_offline_search_needs_no_api(self):
        output = io.StringIO()
        with (
            patch("sys.stdout", output),
            patch("agent.llm_client.Settings.load") as config,
        ):
            code = run_agent.main(["--search-knowledge", "PUE", "--json"])
        config.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["hits"][0]["id"], "pue")
