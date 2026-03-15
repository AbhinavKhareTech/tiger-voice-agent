.PHONY: setup run stop test seed trigger call logs clean lint

# ---- Setup ----
setup:
	@echo "Setting up Tiger Voice Agent..."
	cp -n .env.example .env 2>/dev/null || true
	docker compose build
	@echo "Done. Run 'make run' to start."

# ---- Run ----
run:
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@docker compose ps
	@echo ""
	@echo "Services running:"
	@echo "  Orchestrator:  http://localhost:8000"
	@echo "  Mock Backends: http://localhost:8001"
	@echo "  Redis:         localhost:6379"
	@echo ""
	@echo "Run 'make seed' to load test data."

stop:
	docker compose down

restart:
	docker compose restart

# ---- Data ----
seed:
	@echo "Seeding test customers..."
	python scripts/seed.py
	@echo "Done. Test customers loaded."

# ---- Events ----
trigger:
	@echo "Triggering a card_approved event for test customer..."
	python scripts/trigger_event.py --event card_approved --customer TC001
	@echo "Event published."

# ---- Voice ----
call:
	@echo "Initiating test call via Vapi..."
	python scripts/test_call.py
	@echo "Call initiated. Check orchestrator logs."

# ---- Testing ----
test:
	cd orchestrator && python -m pytest tests/ -v --tb=short
	@echo "All tests passed."

lint:
	cd orchestrator && python -m ruff check src/ tests/
	cd mock_backends && python -m ruff check src/

# ---- Logs ----
logs:
	docker compose logs -f

logs-orchestrator:
	docker compose logs -f orchestrator

logs-backends:
	docker compose logs -f mock-backends

# ---- Cleanup ----
clean:
	docker compose down -v
	@echo "Containers and volumes removed."

# ---- Demo ----
demo: run seed
	@sleep 2
	@echo ""
	@echo "=== Tiger Voice Agent Demo ==="
	@echo "System is ready. Seed data loaded."
	@echo ""
	@echo "Try these:"
	@echo "  curl http://localhost:8001/api/customers/TC001"
	@echo "  curl http://localhost:8000/health"
	@echo "  make trigger  (simulate a stage-change event)"
	@echo "  make call     (initiate a real voice call via Vapi)"
