"""C01 backend registry tests — real backends only, identity + no silent fallback."""
from __future__ import annotations

import unittest

from training.backend_baseline import BackendError
from training.backend_registry import (
    config_hash,
    enumerate_backends,
    get_backend,
    make_llama_server_fn,
    make_unitary_fn,
    prompt_sha256,
    probe_health,
)


class RegistryShapeTests(unittest.TestCase):
    def test_lists_real_backends_not_hypothetical_ones(self):
        ids = {b.identity.backend_id for b in enumerate_backends()}
        self.assertIn("llama-server", ids)
        self.assertIn("native-cautreo", ids)
        self.assertIn("unitary-llm-client", ids)

    def test_roles_match_c01_intent(self):
        roles = {b.identity.backend_id: b.role for b in enumerate_backends()}
        self.assertEqual(roles["llama-server"], "reference-candidate")
        self.assertEqual(roles["native-cautreo"], "isolated-unverified")
        self.assertEqual(roles["unitary-llm-client"], "delegate-pool")

    def test_native_identity_carries_isolation_note(self):
        native = get_backend("native-cautreo").identity
        self.assertIn("UNVERIFIED", str(native.extra.get("semantic_parity")))
        self.assertIn("§2.1", str(native.extra.get("scope")))

    def test_unitary_identity_declares_no_fallback(self):
        extra = get_backend("unitary-llm-client").identity.extra
        self.assertFalse(extra.get("fallback"))
        self.assertIn("DO NOT USE", str(extra.get("isolated_path")))

    def test_llama_server_defaults_do_not_change_port_or_model(self):
        ident = get_backend("llama-server").identity
        self.assertIn("8080", ident.base_url)
        self.assertTrue(ident.model_alias)  # from VIVY_MODEL / gemma4-e4b
        self.assertTrue(ident.config_hash)

    def test_unknown_backend_raises(self):
        with self.assertRaises(KeyError):
            get_backend("gpt-9000")

    def test_config_hash_stable_and_sensitive(self):
        a = config_hash({"temperature": 0.15})
        b = config_hash({"temperature": 0.15})
        c = config_hash({"temperature": 0.9})
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 64)

    def test_prompt_sha256_stable(self):
        self.assertEqual(prompt_sha256("2+2"), prompt_sha256("2+2"))
        self.assertNotEqual(prompt_sha256("2+2"), prompt_sha256("3+3"))


class NoSilentFallbackAdapterTests(unittest.TestCase):
    def test_llama_adapter_maps_dead_port_to_infra_verdict(self):
        """Dead port is infra (unavailable/timeout), never a model FAIL or a fallback."""
        fn = make_llama_server_fn(base_url="http://127.0.0.1:1", timeout_s=2.0)
        with self.assertRaises(BackendError) as ctx:
            fn("hi", 8)
        self.assertIn(ctx.exception.kind, ("unavailable", "timeout"))
        self.assertNotEqual(ctx.exception.kind, "fail")

    def test_unitary_adapter_maps_dead_port_to_infra_verdict(self):
        fn = make_unitary_fn(base_url="http://127.0.0.1:1", model="only-this-model", timeout_s=2.0)
        with self.assertRaises(BackendError) as ctx:
            fn("hi", 8)
        self.assertIn(ctx.exception.kind, ("unavailable", "timeout"))

    def test_adapters_are_single_model_closures(self):
        """No catalogue walk: the closure pins one model_alias."""
        fn = make_llama_server_fn(base_url="http://127.0.0.1:1", model_alias="gemma4-e4b")
        self.assertTrue(callable(fn))
        fn2 = make_unitary_fn(base_url="http://127.0.0.1:1", model="only-this-model")
        self.assertTrue(callable(fn2))


class HealthProbeTests(unittest.TestCase):
    def test_probe_does_not_raise_on_unreachable(self):
        report = probe_health("llama-server", timeout_s=0.5)
        self.assertIn("backend_id", report)
        self.assertEqual(report["backend_id"], "llama-server")
        self.assertIn("reachable", report)

    def test_native_probe_is_explicit_not_a_fake_health_check(self):
        report = probe_health("native-cautreo")
        self.assertIsNone(report["reachable"])
        self.assertIn("receipts", report["detail"])


if __name__ == "__main__":
    unittest.main()
