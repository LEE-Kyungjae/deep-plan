PYTHON ?= python3
PYCACHE_PREFIX ?= /tmp/pycache

.PHONY: test scaffold-test compile scaffold-compile check schema-check package-check

test:
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) $(PYTHON) -m unittest tests.test_deepplan tests.test_deepplan_server tests.test_deepplan_client tests.test_contracts

scaffold-test:
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) $(PYTHON) -m unittest scaffolds.deepplan_agents.tests.test_registry scaffolds.deepplan_agents.tests.test_adapter_and_planner_loop scaffolds.deepplan_agents.tests.test_console scaffolds.deepplan_agents.tests.test_strategy_prompt scaffolds.deepplan_agents.tests.test_strategy_llm scaffolds.deepplan_agents.tests.test_strategy_routes

compile:
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) $(PYTHON) -m py_compile deepplan.py deepplan_store.py deepplan_agent.py deepplan_server.py deepplan_client.py deepplan_sdk/__init__.py deepplan_sdk/client.py examples/deepplan_kernel_adapter.py examples/deepplan_planner_host.py tests/test_deepplan.py tests/test_deepplan_server.py tests/test_deepplan_client.py tests/test_contracts.py

scaffold-compile:
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) PYTHONPATH=scaffolds/deepplan_agents/src $(PYTHON) -m py_compile scaffolds/deepplan_agents/src/deepplan_agents/console.py scaffolds/deepplan_agents/src/deepplan_agents/runtime/host_step.py scaffolds/deepplan_agents/src/deepplan_agents/workflows/planner_loop.py scaffolds/deepplan_agents/src/deepplan_agents/workflows/strategy_loop.py scaffolds/deepplan_agents/src/deepplan_agents/workflows/research_loop.py scaffolds/deepplan_agents/src/deepplan_agents/workflows/review_loop.py scaffolds/deepplan_agents/src/deepplan_agents/skills/registry.py scaffolds/deepplan_agents/src/deepplan_agents/strategy_prompt.py scaffolds/deepplan_agents/src/deepplan_agents/strategy_llm.py scaffolds/deepplan_agents/src/deepplan_agents/strategy_routes.py

check: compile scaffold-compile test scaffold-test

schema-check:
	$(PYTHON) deepplan.py schema --check

package-check:
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) $(PYTHON) -m py_compile deepplan_sdk/__init__.py deepplan_sdk/client.py
