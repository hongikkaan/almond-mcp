"""Emit actual offline algorithm outcomes for the production native adapter fixture."""
import json
from pathlib import Path
import sys
from test_rollback_contract import rollback_outcome
from test_response_budget import budget_outcome

outcomes = {case:rollback_outcome(case) for case in ('undelete', 'cleanup', 'registry-restore', 'move')}
outcomes['budget'] = budget_outcome(layer='긴한국어레이어'*1200)[0]
outcomes['preflight'] = budget_outcome(source_error=True)[0]
Path(sys.argv[1]).write_text(json.dumps(outcomes), encoding='utf-8')
